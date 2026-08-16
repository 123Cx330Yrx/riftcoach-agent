from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.runtime.models import (
    CostObservation,
    RuntimeArtifactReference,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
    RuntimePricingProfile,
    RuntimePublicationStatus,
    TokenObservation,
)
from app.runtime.recorder import RuntimeRecorder, RuntimeRecorderError
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    EvaluationCompletedSignal,
    HarnessTransitionedSignal,
    ContextBuiltSignal,
    ExecutionValidatedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
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
    ToolCallCompletedSignal,
    ToolCallStartedSignal,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
UTC = timezone.utc


class StepUtcClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 8, 15, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(milliseconds=25)
        return value


class StepMonotonic:
    def __init__(self) -> None:
        self.current = 10.0

    def __call__(self) -> float:
        value = self.current
        self.current += 0.025
        return value


def recorder(
    *,
    event_budget: int = 256,
    pricing_profile: RuntimePricingProfile | None = None,
) -> RuntimeRecorder:
    return RuntimeRecorder(
        run_id="runtime_recorder_demo",
        event_budget=event_budget,
        pricing_profile=pricing_profile,
        utc_now=StepUtcClock(),
        monotonic=StepMonotonic(),
    )


def start(rec: RuntimeRecorder) -> None:
    rec.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    rec.emit(
        ExecutionValidatedSignal(
            input_artifact_sha256s=(SHA_A, SHA_B),
        )
    )
    rec.emit(
        ContextBuiltSignal(
            context_contract_version="1.0.0",
            estimated_context_units=8000,
        )
    )


def start_agent(rec: RuntimeRecorder) -> None:
    start(rec)
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.CREATED,
            to_status=RuntimeHarnessStatus.FACTS_READY,
            revision_count=0,
        )
    )


def complete(rec: RuntimeRecorder) -> None:
    rec.emit(
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus.COMPLETED,
            stop_reason=RuntimeAgentStopReason.FINAL_RESPONSE,
            iterations=1,
        )
    )
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.FACTS_READY,
            to_status=RuntimeHarnessStatus.KNOWLEDGE_READY,
            revision_count=0,
        )
    )
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.KNOWLEDGE_READY,
            to_status=RuntimeHarnessStatus.DRAFT_READY,
            revision_count=0,
        )
    )
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.DRAFT_READY,
            to_status=RuntimeHarnessStatus.EVALUATING,
            revision_count=0,
        )
    )
    rec.emit(
        EvaluationCompletedSignal(
            attempt=0,
            score=90,
            verdict=RuntimeEvaluationVerdict.PASS,
        )
    )
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.EVALUATING,
            to_status=RuntimeHarnessStatus.PASSED,
            revision_count=0,
        )
    )
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.PASSED,
            to_status=RuntimeHarnessStatus.PUBLISHED,
            revision_count=0,
        )
    )
    rec.emit(
        PublicationDecidedSignal(
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            artifact_sha256s=(SHA_A,),
        )
    )
    rec.emit(
        RunCompletedSignal(
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
        )
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


def final_artifact() -> RuntimeArtifactReference:
    return RuntimeArtifactReference(
        kind="final_report",
        schema_version="1.0",
        relative_path="output/final_report.md",
        sha256=SHA_A,
        producer="review_harness",
    )


def test_recorder_assigns_ordered_events_and_injected_time():
    rec = recorder()

    start(rec)

    assert tuple(row.sequence for row in rec.events) == (1, 2, 3)
    assert tuple(row.elapsed_ms for row in rec.events) == (0, 25, 50)
    assert all(row.occurred_at_utc.utcoffset() == timedelta(0) for row in rec.events)


def test_first_event_must_be_run_started():
    rec = recorder()

    with pytest.raises(RuntimeRecorderError, match="first event"):
        rec.emit(
            ContextBuiltSignal(
                context_contract_version="1.0.0",
                estimated_context_units=1,
            )
        )


def test_context_cannot_skip_execution_validation():
    rec = recorder()
    rec.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )

    with pytest.raises(RuntimeRecorderError, match="validated execution"):
        rec.emit(
            ContextBuiltSignal(
                context_contract_version="1.0.0",
                estimated_context_units=1,
            )
        )


def test_provider_call_must_start_before_completion():
    rec = recorder()
    start(rec)

    with pytest.raises(RuntimeRecorderError, match="not open"):
        rec.emit(
            ProviderCallCompletedSignal(
                provider_id="offline-fake",
                model="fake-v1",
                ordinal=1,
                finish_reason="stop",
                input_tokens=10,
                output_tokens=2,
            )
        )


def test_terminal_rejects_open_provider_call_and_later_events():
    rec = recorder()
    start_agent(rec)
    rec.emit(
        ProviderCallStartedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            iteration=1,
        )
    )

    with pytest.raises(RuntimeRecorderError, match="open"):
        rec.emit(
            RunFailedSignal(
                failure_stage=RuntimeFailureStage.AGENT,
                failure_code="provider_failed",
            )
        )

    rec.emit(
        ProviderCallFailedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            failure_code="provider_failed",
            provider_error_code="response_invalid",
        )
    )
    rec.emit(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.AGENT,
            failure_code="provider_failed",
        )
    )

    with pytest.raises(RuntimeRecorderError, match="terminal"):
        rec.emit(
            ContextBuiltSignal(
                context_contract_version="1.0.0",
                estimated_context_units=1,
            )
        )


def test_event_budget_fails_closed_before_append():
    rec = recorder(event_budget=2)
    rec.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    with pytest.raises(RuntimeRecorderError, match="terminal"):
        rec.emit(
            ExecutionValidatedSignal(
                input_artifact_sha256s=(SHA_A, SHA_B),
            )
        )
    rec.emit(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.BOUNDARY,
            failure_code="execution_validation_failed",
        )
    )
    assert len(rec.events) == 2


def test_prepared_terminal_is_hidden_and_commit_reuses_the_exact_event():
    rec = recorder(event_budget=2)
    rec.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    before = rec.events

    candidate = rec.prepare_terminal(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.BOUNDARY,
            failure_code="execution_validation_failed",
        )
    )

    assert rec.events == before
    assert candidate.event.sequence == 2
    prospective = rec.build_trace(
        identity=identity(),
        policy=policy(event_budget=2),
        terminal_candidate=candidate,
    )
    assert prospective.events[:-1] == before
    assert prospective.events[-1] == candidate.event

    committed = rec.commit_terminal(candidate)
    assert committed == candidate.event
    assert rec.events[-1] == prospective.events[-1]
    with pytest.raises(RuntimeRecorderError, match="candidate"):
        rec.commit_terminal(candidate)
    with pytest.raises(RuntimeRecorderError, match="candidate"):
        rec.abort_terminal(candidate)


def test_pending_terminal_blocks_mutation_and_abort_allows_failure_terminal():
    rec = recorder(event_budget=3)
    rec.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    candidate = rec.prepare_terminal(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.BOUNDARY,
            failure_code="execution_validation_failed",
        )
    )

    with pytest.raises(RuntimeRecorderError, match="pending"):
        rec.emit(
            ExecutionValidatedSignal(
                input_artifact_sha256s=(SHA_A, SHA_B),
            )
        )
    with pytest.raises(RuntimeRecorderError, match="pending"):
        rec.prepare_terminal(
            RunFailedSignal(
                failure_stage=RuntimeFailureStage.OBSERVABILITY,
                failure_code="observation_failed",
            )
        )

    rec.abort_terminal(candidate)
    with pytest.raises(RuntimeRecorderError, match="candidate"):
        rec.commit_terminal(candidate)
    with pytest.raises(RuntimeRecorderError, match="candidate"):
        rec.abort_terminal(candidate)
    rec.emit(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.OBSERVABILITY,
            failure_code="trace_persistence_failed",
        )
    )

    assert all(
        not (
            isinstance(event.signal, RunFailedSignal)
            and event.signal.failure_code == "execution_validation_failed"
        )
        for event in rec.events
    )
    assert rec.events[-1].signal.failure_code == "trace_persistence_failed"


def test_terminal_candidate_is_bound_to_its_recorder():
    first = recorder(event_budget=2)
    second = recorder(event_budget=2)
    for rec in (first, second):
        rec.emit(
            RunStartedSignal(
                skill_name="recent-form-review",
                skill_version="0.2.0",
                runtime_policy_version="1.0.0",
            )
        )
    candidate = first.prepare_terminal(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.BOUNDARY,
            failure_code="execution_validation_failed",
        )
    )

    with pytest.raises(RuntimeRecorderError, match="candidate"):
        second.commit_terminal(candidate)


def test_harness_transition_evaluation_and_publication_order_is_checked():
    rec = recorder()
    start(rec)
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.CREATED,
            to_status=RuntimeHarnessStatus.FACTS_READY,
            revision_count=0,
        )
    )

    with pytest.raises(RuntimeRecorderError, match="Harness transition"):
        rec.emit(
            HarnessTransitionedSignal(
                from_status=RuntimeHarnessStatus.CREATED,
                to_status=RuntimeHarnessStatus.KNOWLEDGE_READY,
                revision_count=0,
            )
        )
    with pytest.raises(RuntimeRecorderError, match="evaluating"):
        rec.emit(
            EvaluationCompletedSignal(
                attempt=0,
                score=90,
                verdict=RuntimeEvaluationVerdict.PASS,
            )
        )
    with pytest.raises(RuntimeRecorderError, match="terminal Harness"):
        rec.emit(
            PublicationDecidedSignal(
                publication_status=RuntimePublicationStatus.DEGRADED,
                terminal_reason="draft_preparation_failed",
                artifact_sha256s=(SHA_A,),
            )
        )


def test_failed_runtime_preserves_terminal_harness_publication_truth():
    rec = recorder()
    start_agent(rec)
    rec.emit(
        AgentRunTerminatedSignal(
            status=RuntimeAgentStatus.FAILED,
            stop_reason=RuntimeAgentStopReason.PROVIDER_ERROR,
            iterations=0,
            error_code="provider_failed",
        )
    )
    rec.emit(
        HarnessTransitionedSignal(
            from_status=RuntimeHarnessStatus.FACTS_READY,
            to_status=RuntimeHarnessStatus.DEGRADED,
            revision_count=0,
        )
    )

    with pytest.raises(RuntimeRecorderError, match="terminal Harness"):
        rec.emit(
            RunFailedSignal(
                failure_stage=RuntimeFailureStage.OBSERVABILITY,
                failure_code="observation_failed",
            )
        )

    terminal = rec.emit(
        RunFailedSignal(
            failure_stage=RuntimeFailureStage.OBSERVABILITY,
            failure_code="observation_failed",
            publication_status=RuntimePublicationStatus.DEGRADED,
        )
    )
    assert terminal.signal.publication_status is RuntimePublicationStatus.DEGRADED


@pytest.mark.parametrize(
    ("mode", "expected_observation", "expected_input", "expected_observed"),
    (
        ("none", TokenObservation.NOT_APPLICABLE, 0, 0),
        ("complete", TokenObservation.COMPLETE, 100, 100),
        ("partial", TokenObservation.PARTIAL, None, 100),
        ("unknown", TokenObservation.UNKNOWN, None, 0),
    ),
)
def test_usage_does_not_turn_unknown_provider_usage_into_zero(
    mode: str,
    expected_observation: TokenObservation,
    expected_input: int | None,
    expected_observed: int,
):
    rec = recorder()
    start_agent(rec)
    if mode != "none":
        rec.emit(
            ProviderCallStartedSignal(
                provider_id="offline-fake",
                model="fake-v1",
                ordinal=1,
                iteration=1,
            )
        )
        if mode in {"complete", "partial"}:
            rec.emit(
                ProviderCallCompletedSignal(
                    provider_id="offline-fake",
                    model="fake-v1",
                    ordinal=1,
                    finish_reason="stop",
                    input_tokens=100,
                    output_tokens=20,
                )
            )
        else:
            rec.emit(
                ProviderCallFailedSignal(
                    provider_id="offline-fake",
                    model="fake-v1",
                    ordinal=1,
                    failure_code="provider_failed",
                )
            )
        if mode == "partial":
            rec.emit(
                ProviderCallStartedSignal(
                    provider_id="offline-fake",
                    model="fake-v1",
                    ordinal=2,
                    iteration=2,
                )
            )
            rec.emit(
                ProviderCallFailedSignal(
                    provider_id="offline-fake",
                    model="fake-v1",
                    ordinal=2,
                    failure_code="provider_failed",
                )
            )
    complete(rec)

    usage = rec.usage

    assert usage.token_observation is expected_observation
    assert usage.input_tokens == expected_input
    assert usage.observed_input_tokens == expected_observed


def test_tool_usage_counts_calls_attempts_and_latency():
    rec = recorder()
    start_agent(rec)
    rec.emit(
        ToolCallStartedSignal(
            tool_name="knowledge.search",
            tool_version="1.0.0",
            ordinal=1,
            iteration=1,
        )
    )
    rec.emit(
        ToolCallCompletedSignal(
            tool_name="knowledge.search",
            tool_version="1.0.0",
            ordinal=1,
            success=True,
            attempts=2,
            latency_ms=35,
            cached=False,
            fallback_used=True,
        )
    )
    complete(rec)

    assert rec.usage.tool_calls == 1
    assert rec.usage.tool_attempts == 2
    assert rec.usage.tool_latency_ms == 35


def test_cached_tool_result_preserves_zero_attempts_and_fractional_latency():
    rec = recorder()
    start_agent(rec)
    rec.emit(
        ToolCallStartedSignal(
            tool_name="knowledge.search",
            tool_version="1.0.0",
            ordinal=1,
            iteration=1,
        )
    )
    rec.emit(
        ToolCallCompletedSignal(
            tool_name="knowledge.search",
            tool_version="1.0.0",
            ordinal=1,
            success=True,
            attempts=0,
            latency_ms=0.25,
            cached=True,
            fallback_used=False,
        )
    )
    complete(rec)

    assert rec.usage.tool_attempts == 0
    assert rec.usage.tool_latency_ms == 0.25


def test_versioned_pricing_computes_decimal_cost_only_for_complete_usage():
    pricing = RuntimePricingProfile(
        profile_id="offline-fake-standard",
        version="1.0.0",
        provider_id="offline-fake",
        model="fake-v1",
        currency="USD",
        input_cost_per_million=Decimal("2"),
        output_cost_per_million=Decimal("10"),
    )
    rec = recorder(pricing_profile=pricing)
    start_agent(rec)
    rec.emit(
        ProviderCallStartedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            iteration=1,
        )
    )
    rec.emit(
        ProviderCallCompletedSignal(
            provider_id="offline-fake",
            model="fake-v1",
            ordinal=1,
            finish_reason="stop",
            input_tokens=1_000_000,
            output_tokens=100_000,
        )
    )
    complete(rec)

    assert rec.usage.cost_observation is CostObservation.COMPLETE
    assert rec.usage.cost == Decimal("3")
    assert rec.usage.currency == "USD"


def test_pricing_mismatch_is_rejected_before_usage_is_claimed():
    pricing = RuntimePricingProfile(
        profile_id="other-model",
        version="1.0.0",
        provider_id="offline-fake",
        model="other-v1",
        currency="USD",
        input_cost_per_million=Decimal("1"),
        output_cost_per_million=Decimal("1"),
    )
    rec = recorder(pricing_profile=pricing)
    start_agent(rec)

    with pytest.raises(RuntimeRecorderError, match="pricing"):
        rec.emit(
            ProviderCallStartedSignal(
                provider_id="offline-fake",
                model="fake-v1",
                ordinal=1,
                iteration=1,
            )
        )


def test_recorder_builds_terminal_trace_from_one_source_of_events():
    rec = recorder()
    start_agent(rec)
    complete(rec)

    trace = rec.build_trace(
        identity=identity(),
        policy=policy(),
        artifacts=(final_artifact(),),
    )

    assert trace.events == rec.events
    assert trace.usage == rec.usage
    assert trace.elapsed_ms == rec.events[-1].elapsed_ms
    assert trace.runtime_status.value == "completed"
