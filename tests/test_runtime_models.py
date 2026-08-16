from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from app.harness.models import ArtifactKind
from app.skills.execution import (
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.routing_models import (
    RouteOutcome,
    RouteEvidence,
    RouteReason,
    RouterDecision,
)
from app.runtime.models import (
    RuntimeArtifactReference,
    RuntimeEvent,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
    RuntimePublicationStatus,
    RuntimeRunRequest,
    RuntimeRunResult,
    RuntimeStatus,
    RuntimeTrace,
    RuntimeTraceReference,
    RuntimeUsage,
    TokenObservation,
    CostObservation,
)
from app.runtime.signals import (
    ContextBuiltSignal,
    ExecutionValidatedSignal,
    ProviderCallFailedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunStartedSignal,
)


UTC = timezone.utc
SHA_A = "a" * 64
SHA_B = "b" * 64


class DemoOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: str


def execution_request(run_id: str = "runtime_contract_demo") -> SkillExecutionRequest:
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary={"schema_version": "1.0"},
        deterministic_report="facts",
    )
    decision = RouterDecision(
        outcome=RouteOutcome.SELECTED,
        reason=RouteReason.MATCHED_SKILL,
        selected_skill="recent-form-review",
        selected_skill_version="0.2.0",
        candidate_skills=("recent-form-review",),
        evidence=(
            RouteEvidence(
                skill_name="recent-form-review",
                positive_signals=("最近",),
            ),
        ),
        explanation="One Skill matched.",
    )
    return SkillExecutionRequest(
        run_id=run_id,
        user_utterance="分析最近几局",
        router_decision=decision,
        input_payload={"placeholder": True},
        input_artifacts=binding,
    )


def policy(event_budget: int = 256) -> RuntimePolicySnapshot:
    return RuntimePolicySnapshot(
        policy_version="1.0.0",
        event_budget=event_budget,
        max_iterations=4,
        max_tool_calls=3,
        timeout_s=30,
        max_context_tokens=16000,
        publish_score_threshold=85,
        max_revisions=1,
        allow_deterministic_fallback=True,
    )


def identity() -> RuntimeIdentitySnapshot:
    return RuntimeIdentitySnapshot(
        skill_name="recent-form-review",
        skill_version="0.2.0",
        context_contract_version="1.0.0",
        prompt_profile_id="recent-form-coach",
        prompt_profile_version="1.0.0",
        provider_id="offline-fake",
        provider_model="fake-v1",
        harness_version="1.0.0",
    )


def event(sequence: int, signal, *, elapsed_ms: int) -> RuntimeEvent:
    return RuntimeEvent(
        event_schema_version="1.0",
        run_id="runtime_contract_demo",
        sequence=sequence,
        occurred_at_utc=datetime(2026, 8, 15, tzinfo=UTC)
        + timedelta(milliseconds=elapsed_ms),
        elapsed_ms=elapsed_ms,
        signal=signal,
    )


def complete_usage() -> RuntimeUsage:
    return RuntimeUsage(
        provider_calls_attempted=0,
        provider_responses_observed=0,
        observed_input_tokens=0,
        observed_output_tokens=0,
        input_tokens=0,
        output_tokens=0,
        token_observation=TokenObservation.NOT_APPLICABLE,
        tool_calls=0,
        tool_attempts=0,
        tool_latency_ms=0,
        cost=None,
        currency=None,
        pricing_profile_id=None,
        pricing_profile_version=None,
        cost_observation=CostObservation.NOT_CONFIGURED,
    )


def valid_trace() -> RuntimeTrace:
    events = (
        event(
            1,
            RunStartedSignal(
                skill_name="recent-form-review",
                skill_version="0.2.0",
                runtime_policy_version="1.0.0",
            ),
            elapsed_ms=0,
        ),
        event(
            2,
            ExecutionValidatedSignal(
                input_artifact_sha256s=(SHA_A, SHA_B),
            ),
            elapsed_ms=10,
        ),
        event(
            3,
            ContextBuiltSignal(
                context_contract_version="1.0.0",
                estimated_context_units=8000,
            ),
            elapsed_ms=20,
        ),
        event(
            4,
            PublicationDecidedSignal(
                publication_status=RuntimePublicationStatus.PUBLISHED,
                terminal_reason="quality_gate_passed",
                artifact_sha256s=(SHA_A,),
            ),
            elapsed_ms=30,
        ),
        event(
            5,
            RunCompletedSignal(
                publication_status=RuntimePublicationStatus.PUBLISHED,
                terminal_reason="quality_gate_passed",
            ),
            elapsed_ms=40,
        ),
    )
    return RuntimeTrace(
        trace_schema_version="1.0",
        event_schema_version="1.0",
        run_id="runtime_contract_demo",
        identity=identity(),
        policy=policy(),
        events=events,
        usage=complete_usage(),
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=RuntimePublicationStatus.PUBLISHED,
        terminal_reason="quality_gate_passed",
        artifacts=(
            RuntimeArtifactReference(
                kind=ArtifactKind.FINAL_REPORT.value,
                schema_version="1.0",
                relative_path="output/final_report.md",
                sha256=SHA_A,
                producer="review_harness",
            ),
        ),
        started_at_utc=events[0].occurred_at_utc,
        completed_at_utc=events[-1].occurred_at_utc,
        elapsed_ms=40,
    )


def test_runtime_request_wraps_existing_skill_execution_request():
    execution = execution_request()

    request = RuntimeRunRequest(execution_request=execution, policy=policy())

    assert request.run_id == execution.run_id
    assert request.execution_request == execution
    assert request.policy.event_budget == 256


def test_runtime_contracts_reject_extra_fields():
    with pytest.raises(ValidationError, match="extra"):
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
            prompt="do not persist me",
        )

    payload = valid_trace().model_dump(mode="python")
    payload["raw_response"] = "secret body"
    with pytest.raises(ValidationError, match="extra"):
        RuntimeTrace.model_validate(payload)


@pytest.mark.parametrize(
    "unsafe_path",
    (
        "../outside.json",
        "/absolute.json",
        "folder\\windows.json",
        ".",
        "C:/drive.json",
    ),
)
def test_runtime_artifact_reference_rejects_unsafe_paths(unsafe_path: str):
    with pytest.raises(ValidationError, match="relative_path"):
        RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path=unsafe_path,
            sha256=SHA_A,
            producer="review_harness",
        )


def test_runtime_trace_rejects_non_contiguous_sequence():
    payload = valid_trace().model_dump(mode="python")
    payload["events"][2]["sequence"] = 9

    with pytest.raises(ValidationError, match="sequence"):
        RuntimeTrace.model_validate(payload)


def test_runtime_trace_rejects_event_after_terminal():
    payload = valid_trace().model_dump(mode="python")
    payload["events"] = list(payload["events"])
    payload["events"].append(
        event(
            6,
            ContextBuiltSignal(
                context_contract_version="1.0.0",
                estimated_context_units=1,
            ),
            elapsed_ms=50,
        ).model_dump(mode="python")
    )
    payload["completed_at_utc"] = payload["events"][-1]["occurred_at_utc"]
    payload["elapsed_ms"] = 50

    with pytest.raises(ValidationError, match="terminal"):
        RuntimeTrace.model_validate(payload)


def test_runtime_trace_rejects_terminal_status_mismatch():
    payload = valid_trace().model_dump(mode="python")
    payload["publication_status"] = RuntimePublicationStatus.DEGRADED

    with pytest.raises(ValidationError, match="publication"):
        RuntimeTrace.model_validate(payload)


def test_runtime_usage_rejects_complete_claim_when_provider_response_is_unknown():
    with pytest.raises(ValidationError, match="complete"):
        RuntimeUsage(
            provider_calls_attempted=1,
            provider_responses_observed=0,
            observed_input_tokens=0,
            observed_output_tokens=0,
            input_tokens=0,
            output_tokens=0,
            token_observation=TokenObservation.COMPLETE,
            tool_calls=0,
            tool_attempts=0,
            tool_latency_ms=0,
            cost=None,
            currency=None,
            pricing_profile_id=None,
            pricing_profile_version=None,
            cost_observation=CostObservation.NOT_CONFIGURED,
        )


def test_runtime_trace_rejects_provider_failure_without_matching_start():
    payload = valid_trace().model_dump(mode="python")
    payload["events"] = list(payload["events"])
    payload["events"].insert(
        3,
        event(
            4,
            ProviderCallFailedSignal(
                provider_id="offline-fake",
                model="fake-v1",
                ordinal=1,
                failure_code="provider_failed",
            ),
            elapsed_ms=25,
        ).model_dump(mode="python"),
    )
    for sequence, row in enumerate(payload["events"], start=1):
        row["sequence"] = sequence

    with pytest.raises(ValidationError, match="not open"):
        RuntimeTrace.model_validate(payload)


def test_runtime_trace_rejects_unregistered_publication_artifact():
    payload = valid_trace().model_dump(mode="python")
    payload["artifacts"] = ()

    with pytest.raises(ValidationError, match="artifact"):
        RuntimeTrace.model_validate(payload)


def test_runtime_run_result_keeps_typed_output_and_trace_reference():
    result = RuntimeRunResult[DemoOutput](
        run_id="runtime_contract_demo",
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=RuntimePublicationStatus.PUBLISHED,
        terminal_reason="quality_gate_passed",
        output=DemoOutput(report="safe published report"),
        trace_reference=RuntimeTraceReference(
            run_id="runtime_contract_demo",
            sha256=SHA_A,
        ),
    )

    assert isinstance(result.output, DemoOutput)
    assert result.output.report == "safe published report"


def test_completed_runtime_result_requires_output_and_trace():
    with pytest.raises(ValidationError, match="completed"):
        RuntimeRunResult[DemoOutput](
            run_id="runtime_contract_demo",
            runtime_status=RuntimeStatus.COMPLETED,
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            output=None,
            trace_reference=None,
        )


def test_trace_path_is_fixed_and_cannot_be_injected():
    with pytest.raises(ValidationError):
        RuntimeTraceReference(
            run_id="runtime_contract_demo",
            relative_path="../runtime_trace.json",
            sha256=SHA_A,
        )


def test_valid_trace_is_json_round_trip_safe():
    trace = valid_trace()

    loaded = RuntimeTrace.model_validate_json(trace.model_dump_json())

    assert loaded == trace
    assert Path(loaded.artifacts[0].relative_path).as_posix() == (
        "output/final_report.md"
    )
