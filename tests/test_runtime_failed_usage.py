"""Rejected responses retain known usage without becoming successful calls."""
from dataclasses import replace
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.providers.errors import ProviderResponseError
from app.providers.models import TokenUsage
from app.runtime.models import RuntimeTrace, RuntimePricingProfile
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.signals import (
    ProviderCallCompletedSignal, ProviderCallFailedSignal, ProviderCallFailedUsageSignal,
    ProviderCallStartedSignal, RunFailedSignal,
)
from app.runtime.store import RuntimeTraceStore
from tests.test_runtime_observed_provider import (
    RecordingObserver, ScriptedProvider, _request, _response,
)
from tests.test_runtime_recorder import recorder, start_agent, identity, policy


def failed_usage():
    error = ProviderResponseError(provider="zhipu", code="invalid_json")
    error.observed_usage = TokenUsage(input_tokens=11, output_tokens=7)
    error.observed_usage_identity = ("zhipu", "glm-5.2")
    error.observed_usage_conflict = False
    return error


def test_known_failed_usage_emits_failure_without_response_or_exchange():
    error, observer = failed_usage(), RecordingObserver()
    provider = ObservedLLMProvider(delegate=ScriptedProvider([error]), observer=observer)
    with pytest.raises(ProviderResponseError) as caught:
        provider.chat(_request(agent_loop_iteration=1))
    assert caught.value is error and provider.last_exchange is None
    assert [type(s) for s in observer.signals] == [ProviderCallStartedSignal, ProviderCallFailedUsageSignal]
    signal = observer.signals[-1]
    assert isinstance(signal, ProviderCallFailedSignal)
    assert not isinstance(signal, ProviderCallCompletedSignal)
    assert (signal.input_tokens, signal.output_tokens) == (11, 7)
    assert signal.failure_code == "provider_failed"
    assert not any(word in signal.model_dump_json() for word in ("private prompt", "private response"))


@pytest.mark.parametrize("change", [
    "provider", "model", "identity_missing", "untyped", "conflict",
    "conflict_missing", "invalid_cached", "wrong_response", "boolean",
])
def test_unbound_conflicting_or_invalid_failed_usage_stays_unknown(change):
    error, observer = failed_usage(), RecordingObserver()
    if change == "provider":
        error.provider = "other-provider"
    elif change == "model":
        error.observed_usage_identity = ("zhipu", "other-model")
    elif change == "identity_missing":
        del error.observed_usage_identity
    elif change == "untyped":
        error.observed_usage = {"input_tokens": 11, "output_tokens": 7}
    elif change == "conflict":
        error.observed_usage_conflict = True
    elif change == "conflict_missing":
        del error.observed_usage_conflict
    elif change == "invalid_cached":
        error.observed_usage = TokenUsage(input_tokens=11, output_tokens=7, cached_input_tokens=12)
    elif change == "wrong_response":
        error.observed_response = replace(_response(), model="other-model")
    elif change == "boolean":
        object.__setattr__(error.observed_usage, "input_tokens", True)
    provider = ObservedLLMProvider(delegate=ScriptedProvider([error]), observer=observer)
    with pytest.raises(ProviderResponseError):
        provider.chat(_request(agent_loop_iteration=1))
    assert type(observer.signals[-1]) is ProviderCallFailedSignal
    assert provider.last_exchange is None


@pytest.mark.parametrize("unknown_tail", [False, True])
def test_failed_usage_survives_trace_persistence_and_preserves_unknowns(tmp_path, unknown_tail):
    price = RuntimePricingProfile(profile_id="offline-price", version="1.0.0",
        provider_id="zhipu", model="glm-5.2", currency="CNY",
        input_cost_per_million=Decimal("2"), output_cost_per_million=Decimal("4"))
    rec = recorder(pricing_profile=price)
    start_agent(rec)

    class Observer:
        def observe(self, signal):
            rec.emit(signal)

    outcomes = [failed_usage()]
    if unknown_tail:
        outcomes.append(ProviderResponseError(provider="zhipu", code="timeout"))
    observed = ObservedLLMProvider(delegate=ScriptedProvider(outcomes), observer=Observer())
    for iteration in range(1, 3 if unknown_tail else 2):
        with pytest.raises(ProviderResponseError):
            observed.chat(_request(agent_loop_iteration=iteration))
    rec.emit(RunFailedSignal(failure_stage="agent", failure_code="provider_failed"))
    bound = identity().model_copy(update={"provider_id": "zhipu", "provider_model": "glm-5.2"})
    trace = rec.build_trace(identity=bound, policy=policy())
    assert trace.runtime_status.value == "failed"
    assert trace.usage.provider_responses_observed == 1
    assert trace.usage.observed_input_tokens == 11 and trace.usage.observed_output_tokens == 7
    assert trace.usage.token_observation.value == ("partial" if unknown_tail else "complete")
    assert trace.usage.cost == (None if unknown_tail else Decimal("0.00005"))
    assert trace.usage.input_tokens == (None if unknown_tail else 11)
    store = RuntimeTraceStore(tmp_path, trace.run_id)
    assert store.read_trace(store.write_trace(trace)) == trace
    forged = trace.model_dump(mode="json")
    forged["usage"]["observed_input_tokens"] = 0
    with pytest.raises(ValidationError):
        RuntimeTrace.model_validate(forged)


def test_failed_usage_signal_requires_strict_token_counts():
    with pytest.raises(ValidationError):
        ProviderCallFailedUsageSignal(provider_id="zhipu", model="glm-5.2", ordinal=1,
            failure_code="provider_failed", input_tokens=True, output_tokens=0)
