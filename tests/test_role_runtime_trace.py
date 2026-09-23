from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.runtime.coach_contract import NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT
from app.runtime.models import (
    CostObservation, RuntimeArtifactReference, RuntimeIdentitySnapshot,
    RuntimePolicySnapshot, RuntimeTrace, TokenObservation,
)
from app.runtime.recorder import RuntimeRecorder
from app.runtime.signals import (
    AgentRunTerminatedSignal, ContextBuiltSignal, EvaluationCompletedSignal,
    ExecutionValidatedSignal, HarnessTransitionedSignal,
    ProviderCallCompletedSignal, ProviderCallFailedSignal, ProviderCallStartedSignal,
    PublicationDecidedSignal, RunCompletedSignal, RunFailedSignal, RunStartedSignal,
)
from app.runtime.store import RuntimeTraceStore


def role_trace(*, failed_review=False):
    snapshot = ROLE_COACH_CONTRACT.snapshot()
    descriptor = ROLE_COACH_CONTRACT.descriptor()
    identity = RuntimeIdentitySnapshot(
        coach_contract=snapshot,
        skill_name="recent-form-review", skill_version=descriptor["skill_version"],
        context_contract_version="1.0.0", prompt_profile_id="recent-form-coach",
        prompt_profile_version=descriptor["program_version"], provider_id="zhipu",
        provider_model=descriptor["model"], harness_version="1.1.0",
    )
    policy = RuntimePolicySnapshot(
        coach_contract=snapshot, policy_version="1.2.0", max_iterations=4,
        max_tool_calls=8, timeout_s=300, max_context_tokens=28000,
        publish_score_threshold=85, max_revisions=1, allow_deterministic_fallback=False,
    )
    rec = RuntimeRecorder(run_id="role_trace", model_pricing_profiles=ROLE_COACH_CONTRACT.pricing_profiles)
    rec.emit(RunStartedSignal(skill_name=identity.skill_name,
        skill_version=identity.skill_version, runtime_policy_version=policy.policy_version))
    rec.emit(ExecutionValidatedSignal(input_artifact_sha256s=("a" * 64,)))
    rec.emit(ContextBuiltSignal(context_contract_version=identity.context_contract_version, estimated_context_units=8000))

    def transition(source, target, revision=0):
        rec.emit(HarnessTransitionedSignal(from_status=source, to_status=target, revision_count=revision))

    def call(ordinal, phase, model, *, failed=False):
        rec.emit(ProviderCallStartedSignal(provider_id="zhipu", model=model, ordinal=ordinal,
            phase=phase, iteration=1 if phase == "agent" else None))
        if failed:
            rec.emit(ProviderCallFailedSignal(provider_id="zhipu", model=model, ordinal=ordinal,
                failure_code="provider_failed"))
        else:
            rec.emit(ProviderCallCompletedSignal(provider_id="zhipu", model=model, ordinal=ordinal,
                input_tokens=100, output_tokens=50, finish_reason="stop"))

    transition("created", "facts_ready")
    call(1, "agent", "glm-5.3-flash")
    rec.emit(AgentRunTerminatedSignal(status="completed", stop_reason="final_response", iterations=1))
    transition("facts_ready", "knowledge_ready")
    transition("knowledge_ready", "draft_ready")
    transition("draft_ready", "evaluating")
    call(2, "evaluation", "glm-5.3", failed=failed_review)
    if failed_review:
        rec.emit(RunFailedSignal(failure_stage="evaluation", failure_code="provider_failed"))
        return rec.build_trace(identity=identity, policy=policy)
    call(3, "evaluation_repair", "glm-5.3")
    rec.emit(EvaluationCompletedSignal(attempt=0, score=80, verdict="needs_revision"))
    transition("evaluating", "needs_revision")
    transition("needs_revision", "revising", 1)
    call(4, "revision", "glm-5.3-flash")
    transition("revising", "re_evaluating", 1)
    call(5, "evaluation", "glm-5.3")
    rec.emit(EvaluationCompletedSignal(attempt=1, score=97, verdict="pass"))
    transition("re_evaluating", "passed", 1)
    transition("passed", "published", 1)
    rec.emit(PublicationDecidedSignal(publication_status="published",
        terminal_reason="quality_gate_passed", artifact_sha256s=("b" * 64,)))
    rec.emit(RunCompletedSignal(publication_status="published", terminal_reason="quality_gate_passed"))
    return rec.build_trace(identity=identity, policy=policy, artifacts=(RuntimeArtifactReference(
        kind="final_report", schema_version="1.0", relative_path="output/final_report.md",
        sha256="b" * 64, producer="review_harness"),))


def test_role_trace_persistence_round_trip_prices_actual_model_and_all_roles(tmp_path):
    trace = role_trace()
    assert trace.usage.provider_calls_attempted == 5
    assert trace.usage.input_tokens == 500
    assert trace.usage.output_tokens == 250
    assert trace.usage.cost == Decimal("0.00704")
    store = RuntimeTraceStore(tmp_path, trace.run_id)
    reference = store.write_trace(trace)
    restored = store.read_trace(reference)
    assert restored == trace
    assert restored.identity.coach_contract == ROLE_COACH_CONTRACT.snapshot()
    assert restored.identity.runtime_profile_id is None
    assert [event.signal.model for event in restored.events
            if isinstance(event.signal, ProviderCallStartedSignal)] == [
        "glm-5.3-flash", "glm-5.3", "glm-5.3", "glm-5.3-flash", "glm-5.3",
    ]


def test_role_trace_failed_review_keeps_partial_usage_through_persistence(tmp_path):
    trace = role_trace(failed_review=True)
    assert trace.usage.token_observation is TokenObservation.PARTIAL
    assert trace.usage.cost_observation is CostObservation.PARTIAL
    assert trace.usage.observed_input_tokens == 100
    assert trace.usage.observed_output_tokens == 50
    assert trace.usage.cost is None
    assert trace.usage.input_tokens is None
    store = RuntimeTraceStore(tmp_path, trace.run_id)
    assert store.read_trace(store.write_trace(trace)) == trace


@pytest.mark.parametrize("old_contract", [True, False])
def test_mixed_trace_without_exact_role_contract_remains_rejected(old_contract):
    payload = role_trace().model_dump(mode="python")
    for section in ("identity", "policy"):
        payload[section]["coach_contract"] = NATIVE_COACH_CONTRACT.snapshot().model_dump() if old_contract else None
    payload["identity"]["provider_model"] = "glm-5.3-flash"
    with pytest.raises(ValidationError, match="provider call identity mismatch"):
        RuntimeTrace.model_validate(payload)


@pytest.mark.parametrize("phase,changed", [
    ("agent", {"model": "glm-5.3"}),
    ("evaluation", {"model": "glm-5.3-flash"}),
    ("evaluation_repair", {"model": "unknown-model"}),
    ("revision", {"model": "glm-5.3"}),
    ("evaluation", {"provider_id": "other-provider"}),
])
def test_role_trace_model_allowlist_is_phase_specific(phase, changed):
    payload = role_trace().model_dump(mode="python")
    signal = next(event["signal"] for event in payload["events"]
                  if event["signal"]["kind"] == "provider_call_started" and event["signal"]["phase"] == phase)
    signal.update(changed)
    with pytest.raises(ValidationError, match="provider call identity mismatch"):
        RuntimeTrace.model_validate(payload)


@pytest.mark.parametrize("change", ["roles", "profile", "version"])
def test_role_trace_rejects_untrusted_role_or_thinking_profile_digest(change):
    payload = role_trace().model_dump(mode="python")
    descriptor = ROLE_COACH_CONTRACT.descriptor()
    if change == "roles":
        descriptor["roles"]["review"]["model"] = "unknown-model"
    elif change == "profile":
        descriptor["thinking_profile_id"] = "flash-generation-glm53-review-low-v1"
    else:
        descriptor["version"] = "1.4.6"
    forged_digest = hashlib.sha256(json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for section in ("identity", "policy"):
        payload[section]["coach_contract"]["sha256"] = forged_digest
        if change == "version":
            payload[section]["coach_contract"]["version"] = "1.4.6"
    with pytest.raises(ValidationError, match="trusted contract"):
        RuntimeTrace.model_validate(payload)


def test_role_trace_cannot_claim_single_model_admitted_profile():
    payload = role_trace().model_dump(mode="python")
    payload["identity"].update(runtime_profile_id="glm-5.3-flash-runtime-v2", runtime_profile_version="2.0.0")
    with pytest.raises(ValidationError, match="runtime profile identity"):
        RuntimeTrace.model_validate(payload)


@pytest.mark.parametrize("changed", [
    {"cost": Decimal("0.0011")},
    {"pricing_profile_id": "flash-only-price"},
])
def test_role_trace_rejects_flash_pricing_for_review_calls(changed):
    payload = role_trace().model_dump(mode="python")
    payload["usage"].update(changed)
    with pytest.raises(ValidationError, match="role (cost|pricing)"):
        RuntimeTrace.model_validate(payload)


def test_role_trace_still_rejects_wrong_completion_identity_and_usage():
    payload = role_trace().model_dump(mode="python")
    completion = next(event["signal"] for event in payload["events"]
                      if event["signal"]["kind"] == "provider_call_completed")
    completion["model"] = "glm-5.3"
    with pytest.raises(ValidationError, match="provider call identity mismatch"):
        RuntimeTrace.model_validate(payload)
    payload = role_trace().model_dump(mode="python")
    payload["usage"]["observed_input_tokens"] += 1
    payload["usage"]["input_tokens"] += 1
    with pytest.raises(ValidationError, match="observed token usage"):
        RuntimeTrace.model_validate(payload)
