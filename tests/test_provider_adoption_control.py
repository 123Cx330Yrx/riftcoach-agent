from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.agent.draft import AgentFailureObservation
from app.agent.loop import AgentRunStatus, AgentStopReason
from app.evaluation.provider_adoption import (
    AgentFailureClassification,
    ExperimentBudgetedProvider,
    ExperimentFailureCode,
    ExperimentStopController,
    ProviderBudgetPolicy,
    ProviderResourceLedger,
    ResourceLedgerSnapshot,
    classify_agent_failure,
    classify_provider_error,
    deepseek_experiment_policy,
    zhipu_experiment_policy,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderResponseError, ProviderUnavailableError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
)


def request(max_tokens: int | None = 1) -> ChatRequest:
    return ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "safe fixture"),),
        max_tokens=max_tokens,
    )


@dataclass
class RecordingProvider:
    provider_name: str
    model_name: str
    response: ChatResponse | Exception
    capabilities: ProviderCapabilities = ProviderCapabilities()
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, value: ChatRequest) -> ChatResponse:
        self.requests.append(value)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def response(
    *,
    provider: str,
    model: str,
    input_tokens: int = 1,
    output_tokens: int = 1,
) -> ChatResponse:
    return ChatResponse(
        content="ok",
        provider=provider,
        model=model,
        finish_reason="stop",
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


def controlled_provider(
    *,
    policy: ProviderBudgetPolicy,
    result: ChatResponse | Exception,
    scope: str = "domain",
    clock=None,
):
    provider = RecordingProvider(
        provider_name=policy.provider_id,
        model_name=policy.model,
        response=result,
    )
    controller = ExperimentStopController(
        allowed_provider_ids=(policy.provider_id,)
    )
    ledger = ProviderResourceLedger(policy)
    wrapper = ExperimentBudgetedProvider(
        provider=provider,
        ledger=ledger,
        controller=controller,
        scope=scope,
        **({"clock": clock} if clock is not None else {}),
    )
    return wrapper, provider, ledger, controller


def test_deepseek_sixteenth_call_is_rejected_before_provider():
    policy = deepseek_experiment_policy()
    provider = RecordingProvider(
        provider_name="deepseek",
        model_name=policy.model,
        response=response(provider="deepseek", model=policy.model),
    )
    ledger = ProviderResourceLedger(policy)
    controller = ExperimentStopController(allowed_provider_ids=("deepseek",))
    protocol = ExperimentBudgetedProvider(
        provider=provider,
        ledger=ledger,
        controller=controller,
        scope="adapter_protocol",
    )
    domain = ExperimentBudgetedProvider(
        provider=provider,
        ledger=ledger,
        controller=controller,
        scope="domain",
    )

    for _ in range(3):
        protocol.chat(request())
    for _ in range(12):
        domain.chat(request())
    with pytest.raises(ProviderResponseError) as captured:
        domain.chat(request())

    assert captured.value.code == "external_call_budget_exhausted"
    assert len(provider.requests) == 15
    assert ledger.snapshot().calls_used == 15


def test_zhipu_thirteenth_call_is_rejected_before_provider():
    policy = zhipu_experiment_policy()
    wrapper, provider, ledger, _ = controlled_provider(
        policy=policy,
        result=response(provider="zhipu", model=policy.model),
    )

    for _ in range(12):
        wrapper.chat(request())
    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request())

    assert captured.value.code == "external_call_budget_exhausted"
    assert len(provider.requests) == 12
    assert ledger.snapshot().calls_used == 12


def test_deepseek_protocol_fourth_call_is_rejected_by_scope_budget():
    policy = deepseek_experiment_policy()
    wrapper, provider, _, _ = controlled_provider(
        policy=policy,
        result=response(provider="deepseek", model=policy.model),
        scope="adapter_protocol",
    )

    for _ in range(3):
        wrapper.chat(request())
    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request())

    assert captured.value.code == "external_call_budget_exhausted"
    assert len(provider.requests) == 3


def test_domain_case_fifth_call_is_rejected_before_provider():
    policy = deepseek_experiment_policy()
    provider = RecordingProvider(
        provider_name="deepseek",
        model_name=policy.model,
        response=response(provider="deepseek", model=policy.model),
    )
    ledger = ProviderResourceLedger(policy)
    ledger.register_case(
        "heldout_case_1",
        max_calls=4,
        max_observed_tokens=4000,
    )
    controller = ExperimentStopController(allowed_provider_ids=("deepseek",))
    wrapper = ExperimentBudgetedProvider(
        provider=provider,
        ledger=ledger,
        controller=controller,
        scope="domain",
        case_id="heldout_case_1",
    )

    for _ in range(4):
        wrapper.chat(request())
    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request())

    assert captured.value.code == "external_call_budget_exhausted"
    assert len(provider.requests) == 4
    case = ledger.snapshot().case_resources[0]
    assert case.case_id == "heldout_case_1"
    assert case.calls_used == 4


def test_domain_scope_token_limit_is_enforced_after_settlement():
    policy = deepseek_experiment_policy()
    wrapper, provider, ledger, controller = controlled_provider(
        policy=policy,
        result=response(
            provider="deepseek",
            model=policy.model,
            input_tokens=12_000,
            output_tokens=1,
        ),
    )

    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request())

    assert captured.value.code == "token_budget_exhausted"
    assert len(provider.requests) == 1
    domain = next(
        row for row in ledger.snapshot().scope_tokens if row.scope == "domain"
    )
    assert domain.total_tokens == 12_001
    assert controller.snapshot().provider_stops[0].failure_code is (
        ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED
    )


def test_resource_ledger_can_continue_from_admitted_protocol_snapshot():
    policy = deepseek_experiment_policy()
    provider = RecordingProvider(
        provider_name="deepseek",
        model_name=policy.model,
        response=response(
            provider="deepseek",
            model=policy.model,
            input_tokens=10,
            output_tokens=5,
        ),
    )
    controller = ExperimentStopController(allowed_provider_ids=("deepseek",))
    protocol_ledger = ProviderResourceLedger(policy)
    protocol = ExperimentBudgetedProvider(
        provider=provider,
        ledger=protocol_ledger,
        controller=controller,
        scope="adapter_protocol",
    )
    for _ in range(3):
        protocol.chat(request())

    continued = ProviderResourceLedger(
        policy,
        initial_snapshot=protocol_ledger.snapshot(),
    )
    continued.register_case(
        "heldout_case_1",
        max_calls=4,
        max_observed_tokens=4000,
    )
    domain = ExperimentBudgetedProvider(
        provider=provider,
        ledger=continued,
        controller=ExperimentStopController(
            allowed_provider_ids=("deepseek",)
        ),
        scope="domain",
        case_id="heldout_case_1",
    )
    domain.chat(request())

    snapshot = continued.snapshot()
    assert snapshot.calls_used == 4
    assert snapshot.total_tokens == 60
    assert {
        row.scope: row.calls_used for row in snapshot.scope_calls
    } == {"adapter_protocol": 3, "domain": 1}
    assert {
        row.scope: row.total_tokens for row in snapshot.scope_tokens
    } == {"adapter_protocol": 45, "domain": 15}


def test_missing_max_tokens_is_replaced_with_frozen_output_cap():
    policy = deepseek_experiment_policy()
    wrapper, provider, _, _ = controlled_provider(
        policy=policy,
        result=response(provider="deepseek", model=policy.model),
    )

    wrapper.chat(request(max_tokens=None))

    assert provider.requests[0].max_tokens == 1024


def test_output_cap_is_rejected_before_provider():
    policy = deepseek_experiment_policy()
    wrapper, provider, _, _ = controlled_provider(
        policy=policy,
        result=response(provider="deepseek", model=policy.model),
    )

    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request(max_tokens=1025))

    assert captured.value.code == "token_budget_exhausted"
    assert provider.requests == []


def tiny_policy(**updates) -> ProviderBudgetPolicy:
    values = {
        "provider_id": "deepseek",
        "model": "deepseek-v4-pro",
        "currency": "USD",
        "max_calls": 3,
        "scope_call_limits": {"domain": 3},
        "max_observed_tokens": 10,
        "max_output_tokens_per_request": 4,
        "input_cost_per_million": Decimal("1"),
        "output_cost_per_million": Decimal("2"),
        "max_estimated_cost": Decimal("1"),
        "max_latency_ms": 1000,
    }
    values.update(updates)
    return ProviderBudgetPolicy(**values)


def test_observed_token_overrun_stops_provider_after_settlement():
    policy = tiny_policy()
    wrapper, provider, ledger, controller = controlled_provider(
        policy=policy,
        result=response(
            provider="deepseek",
            model=policy.model,
            input_tokens=6,
            output_tokens=5,
        ),
    )

    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request(max_tokens=4))

    assert captured.value.code == "token_budget_exhausted"
    assert len(provider.requests) == 1
    assert ledger.snapshot().total_tokens == 11
    assert controller.snapshot().provider_stops[0].failure_code is (
        ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED
    )
    with pytest.raises(ProviderResponseError):
        wrapper.chat(request(max_tokens=1))
    assert len(provider.requests) == 1


def test_worst_output_cost_is_checked_before_provider():
    policy = tiny_policy(
        output_cost_per_million=Decimal("1000000"),
        max_estimated_cost=Decimal("3"),
    )
    wrapper, provider, _, _ = controlled_provider(
        policy=policy,
        result=response(provider="deepseek", model=policy.model),
    )

    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request(max_tokens=4))

    assert captured.value.code == "cost_budget_exhausted"
    assert provider.requests == []


def test_sdk_failure_consumes_call_and_usage_failure_stops_provider():
    policy = tiny_policy()
    unavailable = ProviderResponseError(
        provider="deepseek",
        code="provider_usage_unavailable",
    )
    wrapper, provider, ledger, controller = controlled_provider(
        policy=policy,
        result=unavailable,
    )

    with pytest.raises(ProviderResponseError):
        wrapper.chat(request())

    assert ledger.snapshot().calls_used == 1
    assert len(provider.requests) == 1
    assert controller.snapshot().provider_stops[0].failure_code is (
        ExperimentFailureCode.PROVIDER_USAGE_UNAVAILABLE
    )


def test_latency_overrun_is_classified_and_stops_provider():
    times = iter((0.0, 1.5))
    policy = tiny_policy(max_latency_ms=1000)
    wrapper, provider, ledger, _ = controlled_provider(
        policy=policy,
        result=response(provider="deepseek", model=policy.model),
        clock=lambda: next(times),
    )

    with pytest.raises(ProviderResponseError) as captured:
        wrapper.chat(request())

    assert captured.value.code == "latency_budget_exhausted"
    assert len(provider.requests) == 1
    assert ledger.snapshot().latency_ms == 1500


def test_unsafe_publication_globally_stops_every_provider():
    controller = ExperimentStopController(
        allowed_provider_ids=("deepseek", "zhipu")
    )

    controller.record_case_failures(
        provider_id="deepseek",
        failure_codes=(ExperimentFailureCode.UNSAFE_PUBLICATION,),
    )

    snapshot = controller.snapshot()
    assert snapshot.global_stop is ExperimentFailureCode.UNSAFE_PUBLICATION
    for provider_id in ("deepseek", "zhipu"):
        with pytest.raises(ProviderResponseError) as captured:
            controller.require_permitted(provider_id)
        assert captured.value.code == "unsafe_publication"


def test_public_snapshots_forbid_sensitive_or_unknown_fields():
    policy = deepseek_experiment_policy()
    snapshot = ProviderResourceLedger(policy).snapshot()
    payload = snapshot.model_dump(mode="json")

    assert "api_key" not in payload
    assert "prompt" not in payload
    assert "response" not in payload
    with pytest.raises(ValidationError):
        ResourceLedgerSnapshot.model_validate(
            {**payload, "api_key": "sk-secret"}
        )


def test_agent_provider_failure_maps_to_layer_and_safe_provider_taxonomy():
    classification = classify_agent_failure(
        AgentFailureObservation(
            status=AgentRunStatus.FAILED,
            stop_reason=AgentStopReason.PROVIDER_ERROR,
            error_code="authentication_failed",
        )
    )

    assert classification == AgentFailureClassification(
        failure_code=ExperimentFailureCode.AGENT_PROVIDER_FAILED,
        provider_failure_code=(
            ExperimentFailureCode.PROVIDER_AUTHENTICATION_FAILED
        ),
    )


def test_unknown_agent_provider_code_stays_safe_unknown():
    classification = classify_agent_failure(
        AgentFailureObservation(
            status=AgentRunStatus.FAILED,
            stop_reason=AgentStopReason.PROVIDER_ERROR,
            error_code="safe_but_unmapped_code",
        )
    )

    assert classification.provider_failure_code is (
        ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN
    )


def test_unexpected_sdk_error_is_not_misreported_as_service_outage():
    assert classify_provider_error(
        ProviderUnavailableError(
            provider="deepseek",
            code="unexpected_sdk_error",
        )
    ) is ExperimentFailureCode.PROVIDER_ERROR_UNKNOWN
