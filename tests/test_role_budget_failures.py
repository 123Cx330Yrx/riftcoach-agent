"""Failure accounting through the real role router, observer and raw factory."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_explicit_source_projection import VERSION
from app.evaluation.golden_journal import write_new_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from app.runtime.signals import ProviderCallCompletedSignal, ProviderCallFailedSignal


class Observer:
    def __init__(self):
        self.signals = []

    def observe(self, signal):
        self.signals.append(signal)


def request(role="generation", *, iteration=1, max_tokens=32):
    metadata = {"agent_loop_iteration": iteration} if role == "generation" else {
        "review_phase": "native_business_revision" if role == "revision" else "native_business_review",
        "harness_step": "revise" if role == "revision" else "evaluate", "source_projection": VERSION,
    }
    messages = (ChatMessage(role=MessageRole.USER, content="offline request"),)
    if role != 'generation':
        messages = (ChatMessage(role=MessageRole.SYSTEM, content='offline policy'),
            ChatMessage(role=MessageRole.USER, content='[UNTRUSTED DATA]\n{"source_index":{"evidence_by_id":{}}}\n[END UNTRUSTED DATA]'),
            ChatMessage(role=MessageRole.USER, content='offline facts'))
    return ChatRequest(messages=messages,
        max_tokens=max_tokens, timeout_s=300, metadata=metadata)


def build(tmp_path, *, clock=lambda: 0, observer=None):
    def settings(model):
        return SimpleNamespace(model=model, base_url="https://open.bigmodel.cn/api/paas/v4", api_key="offline-fixture")
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings("glm-5.3-flash"),
        reviewer_settings=settings("glm-5.3"), transport_root=tmp_path)
    router = factory("run")
    observer = Observer() if observer is None else observer
    observed = ObservedLLMProvider(delegate=router, observer=observer,
        request_identity=ROLE_COACH_CONTRACT.request_identity)
    budget = CoachBudgetedProvider(observed, coach_contract=ROLE_COACH_CONTRACT, clock=clock)
    return budget, router, observed, observer


def child(sent, *, fail_at=None, failure=None, on_response=None):
    def send(command, raw, *, directory, transport_id, environ, timeout_s):
        req = bridge.REQUEST.validate_json(raw)
        sent.append(req)
        if len(sent) == fail_at and failure in ("timeout", "interrupt"):
            write_new_json(directory / "result.json", dict(state="deadline", transport_id=transport_id))
            if failure == "interrupt":
                raise KeyboardInterrupt()
            raise ProviderTimeoutError(provider="zhipu", code="stream_deadline")
        write_new_json(directory / "result.json", dict(state="complete", transport_id=transport_id))
        response = ChatResponse(content="offline response", provider="zhipu", model=environ["LLM_MODEL"],
            finish_reason="stop", usage=TokenUsage(input_tokens=11, output_tokens=7, cached_input_tokens=5))
        if len(sent) == fail_at and failure == "receipt":
            (directory / "result.json").write_text("malformed", encoding="utf-8")
        if len(sent) == fail_at and failure == "wrong_model":
            response = replace(response, model="glm-5.3-flash")
        if on_response is not None:
            response = on_response(req, response)
        return response
    return send


def assert_stopped_without_more_io(budget, sent):
    counts = budget.calls, budget.tokens, budget.reserved_tokens, len(sent)
    for role in ("generation", "review", "revision"):
        with pytest.raises(ProviderResponseError, match="external_call_budget_exhausted"):
            budget.chat(request(role))
    assert (budget.calls, budget.tokens, budget.reserved_tokens, len(sent)) == counts


def test_complete_review_with_bad_receipt_counts_known_usage_once_and_stops(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent, fail_at=2, failure="receipt"))
    budget, router, observed, observer = build(tmp_path)
    budget.chat(request())
    with pytest.raises(ProviderResponseError, match="integrated_transport_receipt_invalid") as error:
        budget.chat(request("review"))
    assert budget.calls == 2 and budget.tokens == 36 and budget.reserved_tokens == 0 and budget.stopped
    assert error.value.observed_response.usage.cached_input_tokens == 5  # already included in input
    assert router.last_exchange is None and observed.last_exchange is None
    completed = [signal for signal in observer.signals if isinstance(signal, ProviderCallCompletedSignal)]
    assert [(s.ordinal, s.model, s.input_tokens + s.output_tokens) for s in completed] == [
        (1, "glm-5.3-flash", 18), (2, "glm-5.3", 18)]
    assert sum(s.input_tokens + s.output_tokens for s in completed) == budget.tokens
    assert not any(isinstance(s, ProviderCallFailedSignal) for s in observer.signals)
    saved = json.loads((tmp_path / "run/review/response-002.json").read_text())
    assert saved["usage"]["input_tokens"] + saved["usage"]["output_tokens"] == 18
    assert_stopped_without_more_io(budget, sent)


@pytest.mark.parametrize("failure,error_type", [("timeout", ProviderTimeoutError), ("interrupt", KeyboardInterrupt),
                                                ("wrong_model", ProviderResponseError)])
def test_unknown_or_unattributable_usage_keeps_reserved_envelope(tmp_path, monkeypatch, failure, error_type):
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent, fail_at=2, failure=failure))
    budget, router, observed, observer = build(tmp_path)
    budget.chat(request())
    with pytest.raises(error_type):
        budget.chat(request("review"))
    assert budget.calls == 2 and budget.tokens == 18 and budget.stopped
    assert budget.reserved_tokens == estimate_runtime_request_input_ceiling(sent[-1]) + sent[-1].max_tokens
    assert router.last_exchange is None and observed.last_exchange is None
    assert_stopped_without_more_io(budget, sent)


def test_known_response_on_observation_exception_is_settled_without_publishing(tmp_path, monkeypatch):
    # This is the same typed failure handoff used by the observer/router; no
    # fallback provider or accepted Exchange is needed to preserve known usage.
    budget, router, observed, observer = build(tmp_path)
    sent = []
    class ObservationFailed(RuntimeError):
        pass
    def failure(req):
        sent.append(req)
        error = ObservationFailed("offline observation failed")
        error.observed_response = ChatResponse(content="received", provider="zhipu", model="glm-5.3",
            finish_reason="stop", usage=TokenUsage(input_tokens=19, output_tokens=5))
        raise error
    monkeypatch.setattr(observed, "chat", failure)
    with pytest.raises(ObservationFailed):
        budget.chat(request("review"))
    assert budget.calls == 1 and budget.tokens == 24 and budget.reserved_tokens == 0 and budget.stopped
    assert observed.last_exchange is None
    assert_stopped_without_more_io(budget, sent)


def test_provider_error_from_wrong_provider_cannot_settle_attributed_usage(tmp_path, monkeypatch):
    budget, router, observed, observer = build(tmp_path)
    def failure(req):
        error = ProviderResponseError(provider="other", code="offline")
        error.observed_response = ChatResponse(content="received", provider="zhipu", model="glm-5.3",
            finish_reason="stop", usage=TokenUsage(input_tokens=19, output_tokens=5))
        raise error
    monkeypatch.setattr(observed, "chat", failure)
    with pytest.raises(ProviderResponseError):
        budget.chat(request("review"))
    assert budget.tokens == 0 and budget.reserved_tokens > 0 and budget.stopped


def test_single_five_call_budget_is_shared_across_models_and_roles(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent))
    budget, router, observed, observer = build(tmp_path)
    for role in ("generation", "generation", "review", "revision", "review"):
        budget.chat(request(role))
    assert budget.calls == router._calls == 5 and budget.tokens == 90 and budget.reserved_tokens == 0
    assert [a["role"] for a in router.attempts] == ["generation", "generation", "review", "revision", "review"]
    assert_stopped_without_more_io(budget, sent)
    native, roles = NATIVE_COACH_CONTRACT.descriptor(), ROLE_COACH_CONTRACT.descriptor()
    for key in ("max_calls", "total_tokens", "execution_timeout_s", "max_revisions", "request_timeout_s", "max_output_tokens"):
        assert roles[key] == native[key]
    assert (roles["max_calls"], roles["total_tokens"], roles["execution_timeout_s"], roles["max_revisions"]) == (5, 401920, 900, 1)


def test_exhausted_shared_tokens_refuse_next_model_before_transport(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent))
    budget, router, observed, observer = build(tmp_path)
    budget.chat(request())
    budget.tokens = 401919
    with pytest.raises(ProviderResponseError, match="token_budget_exhausted"):
        budget.chat(request("review"))
    assert budget.calls == len(sent) == 1 and budget.reserved_tokens == 0


def test_unsettled_reservation_is_included_in_admission(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent))
    budget, router, observed, observer = build(tmp_path)
    budget.reserved_tokens = 401919
    with pytest.raises(ProviderResponseError, match="token_budget_exhausted"):
        budget.chat(request("review"))
    assert budget.calls == len(sent) == 0 and budget.tokens == 0 and budget.reserved_tokens == 401919


def test_bad_role_before_dispatch_does_not_claim_call_or_reservation(tmp_path):
    budget, router, observed, observer = build(tmp_path)
    with pytest.raises(ValueError, match="role_source_projection_required"):
        budget.chat(replace(request("review"), metadata={"review_phase": "native_business_review"}))
    assert budget.calls == router._calls == budget.tokens == budget.reserved_tokens == 0
    assert budget.stopped and observer.signals == []


def test_whole_task_deadline_clamps_next_model_and_late_reply_keeps_usage(tmp_path, monkeypatch):
    now = [0.0]
    sent = []
    def complete(req, response):
        now[0] = 901
        return response
    monkeypatch.setattr(bridge, "run_child", child(sent, on_response=complete))
    budget, router, observed, observer = build(tmp_path, clock=lambda: now[0])
    now[0] = 890
    with pytest.raises(ProviderResponseError, match="timeout"):
        budget.chat(request("review"))
    assert sent[0].timeout_s == 10
    assert budget.tokens == 18 and budget.reserved_tokens == 0 and budget.calls == 1
    assert_stopped_without_more_io(budget, sent)


def test_pre_call_deadline_does_not_open_any_model(tmp_path):
    now = [0.0]
    budget, router, observed, observer = build(tmp_path, clock=lambda: now[0])
    now[0] = 900
    with pytest.raises(ProviderResponseError, match="timeout"):
        budget.chat(request("review"))
    assert budget.calls == router._calls == budget.tokens == budget.reserved_tokens == 0
    assert observer.signals == []


def test_response_above_envelope_keeps_actual_usage_then_stops(tmp_path, monkeypatch):
    sent = []
    def exceed(req, response):
        return replace(response, usage=TokenUsage(input_tokens=estimate_runtime_request_input_ceiling(req) + 1,
            output_tokens=req.max_tokens + 1))
    monkeypatch.setattr(bridge, "run_child", child(sent, on_response=exceed))
    budget, router, observed, observer = build(tmp_path)
    with pytest.raises(ProviderResponseError, match="token_envelope_exceeded"):
        budget.chat(request("review"))
    assert budget.tokens == estimate_runtime_request_input_ceiling(sent[0]) + sent[0].max_tokens + 2
    assert budget.reserved_tokens == 0 and budget.calls == 1 and budget.stopped
    assert_stopped_without_more_io(budget, sent)


@pytest.mark.parametrize("failed_file", ["response-002.json", "call-result-002.json"])
def test_response_recording_oserror_preserves_usage_in_budget_and_persisted_failed_trace(
        tmp_path, monkeypatch, failed_file):
    from app.runtime.models import RuntimeIdentitySnapshot, RuntimePolicySnapshot, TokenObservation
    from app.runtime.recorder import RuntimeRecorder
    from app.runtime.signals import (
        AgentRunTerminatedSignal, ContextBuiltSignal, ExecutionValidatedSignal,
        HarnessTransitionedSignal, RunFailedSignal, RunStartedSignal,
    )
    from app.runtime.store import RuntimeTraceStore

    descriptor, snapshot = ROLE_COACH_CONTRACT.descriptor(), ROLE_COACH_CONTRACT.snapshot()
    identity = RuntimeIdentitySnapshot(coach_contract=snapshot, skill_name="recent-form-review",
        skill_version=descriptor["skill_version"], context_contract_version="1.0.0",
        prompt_profile_id="recent-form-coach", prompt_profile_version=descriptor["program_version"],
        provider_id="zhipu", provider_model=descriptor["model"], harness_version="1.1.0")
    policy = RuntimePolicySnapshot(coach_contract=snapshot, policy_version="1.2.0",
        max_iterations=4, max_tool_calls=8, timeout_s=300, max_context_tokens=28000,
        publish_score_threshold=85, max_revisions=1, allow_deterministic_fallback=False)
    recorder = RuntimeRecorder(run_id="failed_recording",
        model_pricing_profiles=ROLE_COACH_CONTRACT.pricing_profiles)
    recorder.emit(RunStartedSignal(skill_name=identity.skill_name, skill_version=identity.skill_version,
        runtime_policy_version=policy.policy_version))
    recorder.emit(ExecutionValidatedSignal(input_artifact_sha256s=("a" * 64,)))
    recorder.emit(ContextBuiltSignal(context_contract_version="1.0.0", estimated_context_units=8000))
    recorder.emit(HarnessTransitionedSignal(from_status="created", to_status="facts_ready", revision_count=0))
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent))
    budget, router, observed, _ = build(tmp_path / "transport",
        observer=SimpleNamespace(observe=recorder.emit))
    budget.chat(request())
    recorder.emit(AgentRunTerminatedSignal(status="completed", stop_reason="final_response", iterations=1))
    for source, target in (("facts_ready", "knowledge_ready"), ("knowledge_ready", "draft_ready"),
                           ("draft_ready", "evaluating")):
        recorder.emit(HarnessTransitionedSignal(from_status=source, to_status=target, revision_count=0))

    original_open = Path.open
    cause = OSError("private recording location must not reach the public error")
    def broken_open(path, mode="r", *args, **kwargs):
        if path.name == failed_file and mode == "xb":
            raise cause
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", broken_open)
    with pytest.raises(ProviderResponseError, match="role_response_recording_failed") as failure:
        budget.chat(request("review"))
    assert failure.value.__cause__ is cause
    assert "private recording location" not in str(failure.value)
    assert failure.value.observed_response is router.reviewer.last_response
    assert (budget.calls, budget.tokens, budget.reserved_tokens, budget.stopped) == (2, 36, 0, True)
    assert router.attempts[-1]["error"] == "role_response_recording_failed"
    assert router._failed and router.reviewer._failed
    assert router.last_exchange is observed.last_exchange is router.reviewer.last_exchange is None
    assert not (tmp_path / "transport/run/call-result-002.json").exists()
    recorder.emit(RunFailedSignal(failure_stage="evaluation", failure_code="provider_failed"))
    trace = recorder.build_trace(identity=identity, policy=policy)
    assert trace.runtime_status.value == "failed" and trace.publication_status is None and trace.artifacts == ()
    assert trace.usage.token_observation is TokenObservation.COMPLETE
    assert (trace.usage.input_tokens, trace.usage.output_tokens) == (22, 14)
    assert trace.usage.input_tokens + trace.usage.output_tokens == budget.tokens
    completed = [event.signal for event in trace.events if isinstance(event.signal, ProviderCallCompletedSignal)]
    assert [(event.ordinal, event.model, event.input_tokens, event.output_tokens) for event in completed] == [
        (1, "glm-5.3-flash", 11, 7), (2, "glm-5.3", 11, 7)]
    assert not any(isinstance(event.signal, ProviderCallFailedSignal) for event in trace.events)
    store = RuntimeTraceStore(tmp_path / "trace", trace.run_id)
    assert store.read_trace(store.write_trace(trace)) == trace
    assert_stopped_without_more_io(budget, sent)


def test_router_cancellation_is_reraised_and_blocks_every_other_role(tmp_path, monkeypatch):
    _, router, _, _ = build(tmp_path)
    sent = []
    cancellation = KeyboardInterrupt("cancelled")
    def cancel(*args, **kwargs):
        sent.append(kwargs["environ"]["LLM_MODEL"])
        raise cancellation
    monkeypatch.setattr(bridge, "run_child", cancel)
    with pytest.raises(KeyboardInterrupt) as failure:
        router.chat(request())
    assert failure.value is cancellation
    assert router._failed and router.generator._failed and router.last_exchange is None
    assert router.attempts[-1]["status"] == "failed"
    assert router.attempts[-1]["error"] == "KeyboardInterrupt"
    for role in ("review", "revision", "generation"):
        with pytest.raises(ProviderResponseError, match="role_run_stopped"):
            router.chat(request(role))
    assert sent == ["glm-5.3-flash"] and router._calls == 1


@pytest.mark.parametrize("role,step", [("generation", "evaluate"), ("review", "revise"),
                                       ("revision", "evaluate"), ("revision", None)])
@pytest.mark.parametrize("through_budget", [False, True])
def test_conflicting_role_and_harness_phase_is_rejected_before_transport(
        tmp_path, monkeypatch, role, step, through_budget):
    sent = []
    monkeypatch.setattr(bridge, "run_child", child(sent))
    budget, router, observed, observer = build(tmp_path)
    req = request(role)
    req = replace(req, metadata={**req.metadata, "harness_step": step})
    with pytest.raises(ValueError, match="role_phase_invalid"):
        (budget if through_budget else router).chat(req)
    assert sent == [] and router.attempts == [] and not tmp_path.joinpath("run").exists()
    assert budget.calls == 0 and budget.tokens == 0 and budget.reserved_tokens == 0
    assert observed.last_exchange is router.last_exchange is None
    assert observer.signals == []
    assert budget.stopped if through_budget else router._failed
