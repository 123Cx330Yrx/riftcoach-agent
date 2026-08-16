from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.harness.state_machine import ALLOWED_TRANSITIONS
from app.runtime.lifecycle import RUNTIME_V11_HARNESS_TRANSITIONS
from app.runtime.models import (
    CostObservation,
    RuntimeArtifactReference,
    RuntimeEvent,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
    RuntimeStatus,
    RuntimeTrace,
    RuntimeTraceReference,
    RuntimeUsage,
    TokenObservation,
)
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    ContextBuiltSignal,
    EvaluationCompletedSignal,
    ExecutionValidatedSignal,
    HarnessTransitionedSignal,
    ProviderCallCompletedSignal,
    ProviderCallStartedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunFailedSignal,
    RunStartedSignal,
    RuntimeAgentStatus,
    RuntimeAgentStopReason,
    RuntimeEvaluationVerdict,
    RuntimeFailureStage,
    RuntimeHarnessStatus,
    RuntimeProviderPhase,
    RuntimePublicationStatus,
    ToolCallCompletedSignal,
)


UTC = timezone.utc
SHA_A = "a" * 64


def _event(
    sequence: int,
    signal,
    *,
    schema_version: str = "1.1",
) -> RuntimeEvent:
    return RuntimeEvent(
        event_schema_version=schema_version,
        run_id="runtime_v11_demo",
        sequence=sequence,
        occurred_at_utc=datetime(2026, 8, 16, tzinfo=UTC)
        + timedelta(milliseconds=sequence),
        elapsed_ms=sequence,
        signal=signal,
    )


def _identity() -> RuntimeIdentitySnapshot:
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


def _policy() -> RuntimePolicySnapshot:
    return RuntimePolicySnapshot(
        policy_version="1.0.0",
        event_budget=256,
        max_iterations=4,
        max_tool_calls=3,
        timeout_s=30,
        max_context_tokens=16000,
        publish_score_threshold=85,
        max_revisions=1,
        allow_deterministic_fallback=True,
    )


def _no_provider_usage() -> RuntimeUsage:
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


def _failed_trace(*, schema_version: str = "1.1") -> RuntimeTrace:
    events = (
        _event(
            1,
            RunStartedSignal(
                skill_name="recent-form-review",
                skill_version="0.2.0",
                runtime_policy_version="1.0.0",
            ),
            schema_version=schema_version,
        ),
        _event(
            2,
            RunFailedSignal(
                failure_stage=RuntimeFailureStage.BOUNDARY,
                failure_code="execution_validation_failed",
            ),
            schema_version=schema_version,
        ),
    )
    return RuntimeTrace(
        trace_schema_version=schema_version,
        event_schema_version=schema_version,
        run_id="runtime_v11_demo",
        identity=_identity(),
        policy=_policy(),
        events=events,
        usage=_no_provider_usage(),
        runtime_status=RuntimeStatus.FAILED,
        publication_status=None,
        terminal_reason="execution_validation_failed",
        started_at_utc=events[0].occurred_at_utc,
        completed_at_utc=events[-1].occurred_at_utc,
        elapsed_ms=events[-1].elapsed_ms,
    )


def _published_trace() -> RuntimeTrace:
    signals = (
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        ),
        ExecutionValidatedSignal(input_artifact_sha256s=(SHA_A,)),
        ContextBuiltSignal(
            context_contract_version="1.0.0",
            estimated_context_units=8000,
            omitted_item_ids=("facts:recent_match:01",),
        ),
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.CREATED,
            to_status=RuntimeHarnessStatus.FACTS_READY,
            revision_count=0,
        ),
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus.COMPLETED,
            stop_reason=RuntimeAgentStopReason.FINAL_RESPONSE,
            iterations=1,
        ),
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.FACTS_READY,
            to_status=RuntimeHarnessStatus.KNOWLEDGE_READY,
            revision_count=0,
        ),
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.KNOWLEDGE_READY,
            to_status=RuntimeHarnessStatus.DRAFT_READY,
            revision_count=0,
        ),
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.DRAFT_READY,
            to_status=RuntimeHarnessStatus.EVALUATING,
            revision_count=0,
        ),
        EvaluationCompletedSignal(
            attempt=0,
            score=92,
            verdict=RuntimeEvaluationVerdict.PASS,
        ),
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.EVALUATING,
            to_status=RuntimeHarnessStatus.PASSED,
            revision_count=0,
        ),
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.PASSED,
            to_status=RuntimeHarnessStatus.PUBLISHED,
            revision_count=0,
        ),
        PublicationDecidedSignal(
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            artifact_sha256s=(SHA_A,),
        ),
        RunCompletedSignal(
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
        ),
    )
    events = tuple(
        _event(sequence, signal)
        for sequence, signal in enumerate(signals, start=1)
    )
    return RuntimeTrace(
        run_id="runtime_v11_demo",
        identity=_identity(),
        policy=_policy(),
        events=events,
        usage=_no_provider_usage(),
        runtime_status=RuntimeStatus.COMPLETED,
        publication_status=RuntimePublicationStatus.PUBLISHED,
        terminal_reason="quality_gate_passed",
        artifacts=(
            RuntimeArtifactReference(
                kind="final_report",
                schema_version="1.0",
                relative_path="output/final_report.md",
                sha256=SHA_A,
                producer="review_harness",
            ),
        ),
        started_at_utc=events[0].occurred_at_utc,
        completed_at_utc=events[-1].occurred_at_utc,
        elapsed_ms=events[-1].elapsed_ms,
    )


def test_runtime_writes_schema_11_by_default_and_reads_legacy_10():
    current = _failed_trace()
    legacy = _failed_trace(schema_version="1.0")

    assert current.trace_schema_version == "1.1"
    assert current.event_schema_version == "1.1"
    assert all(event.event_schema_version == "1.1" for event in current.events)
    assert RuntimeTraceReference(
        run_id="runtime_v11_demo",
        sha256=SHA_A,
    ).trace_schema_version == "1.1"
    assert RuntimeTrace.model_validate_json(legacy.model_dump_json()) == legacy


@pytest.mark.parametrize(
    "signal",
    (
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus.COMPLETED,
            stop_reason=RuntimeAgentStopReason.FINAL_RESPONSE,
            iterations=1,
        ),
        ContextBuiltSignal(
            context_contract_version="1.0.0",
            estimated_context_units=1,
            omitted_item_ids=("facts:recent_match:01",),
        ),
        ProviderCallStartedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            phase=RuntimeProviderPhase.EVALUATION,
            iteration=None,
        ),
        ProviderCallCompletedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            finish_reason=None,
            input_tokens=1,
            output_tokens=1,
        ),
        EvaluationCompletedSignal(
            attempt=0,
            score=90,
            verdict=RuntimeEvaluationVerdict.PASS,
        ),
        ToolCallCompletedSignal(
            tool_name="knowledge.search",
            tool_version="1.0.0",
            ordinal=1,
            success=False,
            failure_code="handler_failed",
            attempts=1,
            latency_ms=1,
            cached=False,
            fallback_used=False,
        ),
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.HARNESS,
            failure_code="harness_execution_failed",
        ),
    ),
)
def test_legacy_event_schema_rejects_v11_only_signal_semantics(signal):
    with pytest.raises(ValidationError):
        _event(1, signal, schema_version="1.0")


@pytest.mark.parametrize(
    ("signal_payload", "expected_field", "expected_value"),
    (
        (
            {
                "kind": "provider_call_completed",
                "provider_id": "offline-fake",
                "model": "fake-v1",
                "ordinal": 1,
                "finish_reason": "legacy_vendor_reason",
                "input_tokens": 1,
                "output_tokens": 1,
            },
            "finish_reason",
            "legacy_vendor_reason",
        ),
        (
            {
                "kind": "tool_call_completed",
                "tool_name": "knowledge.search",
                "tool_version": "1.0.0",
                "ordinal": 1,
                "success": False,
                "attempts": 1,
                "latency_ms": 1,
                "cached": False,
                "fallback_used": False,
            },
            "failure_code",
            None,
        ),
        (
            {
                "kind": "publication_decided",
                "publication_status": "published",
                "terminal_reason": "quality_gate_passed",
                "artifact_sha256s": [],
            },
            "artifact_sha256s",
            (),
        ),
    ),
)
def test_legacy_event_schema_reads_shapes_that_were_legal_in_v10(
    signal_payload,
    expected_field,
    expected_value,
):
    event = RuntimeEvent.model_validate(
        {
            "event_schema_version": "1.0",
            "run_id": "runtime_v11_demo",
            "sequence": 1,
            "occurred_at_utc": datetime(2026, 8, 16, tzinfo=UTC),
            "elapsed_ms": 0,
            "signal": signal_payload,
        }
    )

    assert getattr(event.signal, expected_field) == expected_value


def test_runtime_v11_transition_graph_stays_in_sync_with_harness():
    harness_graph = {
        source.value: frozenset(target.value for target in targets)
        for source, targets in ALLOWED_TRANSITIONS.items()
    }
    runtime_graph = {
        source.value: frozenset(target.value for target in targets)
        for source, targets in RUNTIME_V11_HARNESS_TRANSITIONS.items()
    }

    assert runtime_graph == harness_graph


def test_trace_rejects_trace_and_event_schema_version_mismatch():
    payload = _failed_trace().model_dump(mode="python")
    payload["events"][0]["event_schema_version"] = "1.0"

    with pytest.raises(ValidationError, match="event_schema_version"):
        RuntimeTrace.model_validate(payload)

    payload = _failed_trace().model_dump(mode="python")
    payload["trace_schema_version"] = "1.0"
    with pytest.raises(ValidationError, match="schema version"):
        RuntimeTrace.model_validate(payload)


def test_context_section_ids_allow_safe_colon_segments_only():
    signal = ContextBuiltSignal(
        context_contract_version="1.0.0",
        estimated_context_units=1,
        omitted_item_ids=("facts:recent_match:01", "knowledge:citation:003"),
    )
    assert signal.omitted_item_ids == (
        "facts:recent_match:01",
        "knowledge:citation:003",
    )

    for unsafe in ("facts:../secret", "facts: recent", "facts::recent", "/facts"):
        with pytest.raises(ValidationError):
            ContextBuiltSignal(
                context_contract_version="1.0.0",
                estimated_context_units=1,
                omitted_item_ids=(unsafe,),
            )


def test_provider_phase_controls_iteration_and_finish_reason_is_bounded():
    assert ProviderCallStartedSignal(
        provider_id="offline-fake",
        model="fake-v1",
        ordinal=1,
        phase=RuntimeProviderPhase.AGENT,
        iteration=1,
    ).iteration == 1
    assert ProviderCallStartedSignal(
        provider_id="offline-fake",
        model="fake-v1",
        ordinal=1,
        phase=RuntimeProviderPhase.EVALUATION,
        iteration=None,
    ).iteration is None

    with pytest.raises(ValidationError, match="iteration"):
        ProviderCallStartedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            phase=RuntimeProviderPhase.AGENT,
            iteration=None,
        )
    with pytest.raises(ValidationError, match="iteration"):
        ProviderCallStartedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            phase=RuntimeProviderPhase.REVISION,
            iteration=1,
        )

    assert ProviderCallCompletedSignal(
        provider_id="offline-fake",
        model="fake-v1",
        ordinal=1,
        finish_reason=None,
        input_tokens=1,
        output_tokens=1,
    ).finish_reason is None
    with pytest.raises(ValidationError, match="finish_reason"):
        _event(
            1,
            ProviderCallCompletedSignal(
                provider_id="offline-fake",
                model="fake-v1",
                ordinal=1,
                finish_reason="vendor_private_reason",
                input_tokens=1,
                output_tokens=1,
            ),
        )


def test_agent_terminal_and_tool_failure_contracts_reject_inconsistent_shapes():
    AgentRunTerminatedSignal(
        status=RuntimeAgentStatus.COMPLETED,
        stop_reason=RuntimeAgentStopReason.FINAL_RESPONSE,
        iterations=1,
    )
    AgentRunTerminatedSignal(
        status=RuntimeAgentStatus.FAILED,
        stop_reason=RuntimeAgentStopReason.PROVIDER_ERROR,
        iterations=0,
        error_code="provider_failed",
    )

    with pytest.raises(ValidationError, match="completed"):
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus.COMPLETED,
            stop_reason=RuntimeAgentStopReason.TIMEOUT,
            iterations=1,
        )
    with pytest.raises(ValidationError, match="error_code"):
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus.FAILED,
            stop_reason=RuntimeAgentStopReason.PROVIDER_ERROR,
            iterations=0,
        )

    ToolCallCompletedSignal(
        tool_name="knowledge.search",
        tool_version="1.0.0",
        ordinal=1,
        success=False,
        failure_code="handler_failed",
        attempts=1,
        latency_ms=1,
        cached=False,
        fallback_used=False,
    )
    with pytest.raises(ValidationError, match="failure_code"):
        _event(
            1,
            ToolCallCompletedSignal(
                tool_name="knowledge.search",
                tool_version="1.0.0",
                ordinal=1,
                success=False,
                failure_code=None,
                attempts=1,
                latency_ms=1,
                cached=False,
                fallback_used=False,
            ),
        )
    with pytest.raises(ValidationError, match="failure_code"):
        _event(
            1,
            ToolCallCompletedSignal(
                tool_name="knowledge.search",
                tool_version="1.0.0",
                ordinal=1,
                success=True,
                failure_code="handler_failed",
                attempts=1,
                latency_ms=1,
                cached=False,
                fallback_used=False,
            ),
        )


@pytest.mark.parametrize(
    ("publication_status", "artifact_sha256s"),
    (
        (RuntimePublicationStatus.PUBLISHED, ()),
        (RuntimePublicationStatus.DEGRADED, ()),
        (RuntimePublicationStatus.REJECTED, (SHA_A,)),
    ),
)
def test_v11_publication_requires_exact_report_digest_shape(
    publication_status,
    artifact_sha256s,
):
    with pytest.raises(ValidationError, match="publication|report"):
        _event(
            1,
            PublicationDecidedSignal(
                publication_status=publication_status,
                terminal_reason="quality_gate_decided",
                artifact_sha256s=artifact_sha256s,
            ),
        )


def test_evaluation_attempt_is_zero_based_and_harness_is_a_failure_stage():
    assert EvaluationCompletedSignal(
        attempt=0,
        score=90,
        verdict=RuntimeEvaluationVerdict.PASS,
    ).attempt == 0
    assert RuntimeFailureStage.HARNESS.value == "harness"

    with pytest.raises(ValidationError, match="attempt"):
        EvaluationCompletedSignal(
            attempt=-1,
            score=90,
            verdict=RuntimeEvaluationVerdict.PASS,
        )


def test_trace_validates_harness_transition_and_evaluation_order():
    trace = _published_trace()
    assert trace.runtime_status is RuntimeStatus.COMPLETED

    payload = trace.model_dump(mode="python")
    payload["events"][5]["signal"]["from_status"] = "created"
    with pytest.raises(ValidationError, match="Harness transition"):
        RuntimeTrace.model_validate(payload)

    payload = trace.model_dump(mode="python")
    payload["events"][8]["signal"]["attempt"] = 1
    with pytest.raises(ValidationError, match="attempt"):
        RuntimeTrace.model_validate(payload)

    payload = trace.model_dump(mode="python")
    payload["events"][10]["signal"]["to_status"] = "degraded"
    with pytest.raises(ValidationError, match="publication"):
        RuntimeTrace.model_validate(payload)


def test_publication_digest_must_reference_the_final_report_artifact():
    payload = _published_trace().model_dump(mode="python")
    payload["artifacts"][0]["kind"] = "evaluation"

    with pytest.raises(ValidationError, match="no Trace reference"):
        RuntimeTrace.model_validate(payload)
