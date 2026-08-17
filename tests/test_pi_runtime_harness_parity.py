from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.agent.context import ContextBuilderV1
from app.evaluation.pi_runtime import (
    PiAllowedTool,
    PiInputMessage,
    PiRuntimeSignalProjector,
    PiScriptedAssistantStep,
    PiScriptedFailureStep,
    PiScriptedToolCall,
    PiScriptedUsage,
    PiSidecarController,
    PiSkillDraftPreparer,
    PiSpikePolicy,
    PiSpikeRunRequest,
    PiTraceParityError,
)
from app.harness.models import ArtifactKind
from app.harness.store import FileRunStore
from app.harness.steps import EvaluationResult, EvaluationVerdict
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.artifacts import project_artifact_references
from app.runtime.models import RuntimeIdentitySnapshot, RuntimePolicySnapshot
from app.runtime.recorder import RuntimeRecorder
from app.runtime.signals import (
    ContextBuiltSignal,
    ExecutionValidatedSignal,
    RunCompletedSignal,
    RunStartedSignal,
    RuntimePublicationStatus,
)
from app.skills.review_executor import SkillReviewExecutor
from app.tools.adapters import build_knowledge_tools
from app.tools.models import ToolDefinition
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from tests.test_agent_draft_preparer import recent_execution


QUERY = "前15分钟死亡 训练建议"


class PassingEvaluator:
    def __init__(self) -> None:
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        return EvaluationResult(
            score=95,
            verdict=EvaluationVerdict.PASS,
            passed_checks=("fixture_only",),
        )


class UnexpectedEvaluator:
    def evaluate(self, request):
        raise AssertionError("evaluation must not run for an invalid draft")


class UnexpectedReviser:
    def revise(self, request):
        raise AssertionError("revision must not run in this frozen slice")


@dataclass
class RecorderObserver:
    recorder: RuntimeRecorder

    def observe(self, signal) -> None:
        self.recorder.emit(signal)


def _knowledge_runtime():
    provider = LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))
    registry = ToolRegistry()
    for definition in build_knowledge_tools(provider):
        registry.register(definition)
    return registry, ToolRuntime(registry), registry.get("knowledge.search")


def _tool_step() -> PiScriptedAssistantStep:
    return PiScriptedAssistantStep(
        tool_calls=(
            PiScriptedToolCall(
                id="knowledge_1",
                name="knowledge.search",
                arguments={"query": QUERY, "top_k": 2},
            ),
        ),
        usage=PiScriptedUsage(input_tokens=11, output_tokens=5),
    )


def _final_step(text: str = "# Coach draft\n\n谨慎训练建议 [K1]。"):
    return PiScriptedAssistantStep(
        content=text,
        usage=PiScriptedUsage(input_tokens=17, output_tokens=8),
    )


def _direct_request(definition, *, run_id: str, script):
    return PiSpikeRunRequest(
        run_id=run_id,
        system_prompt="Use only the declared coaching knowledge tool.",
        messages=(
            PiInputMessage(
                role="user",
                content="Review the frozen recent-form context.",
            ),
        ),
        allowed_tools=(
            PiAllowedTool(
                name="knowledge.search",
                version="2.0.0",
                description=definition.description,
                input_schema=dict(definition.input_schema),
            ),
        ),
        script=tuple(script),
        policy=PiSpikePolicy(
            max_iterations=4,
            max_tool_calls=3,
            timeout_s=5.0,
            max_context_chars=200_000,
        ),
    )


def _preparer(
    *,
    run_id: str,
    script,
    observer=None,
    max_context_chars: int = 200_000,
    sidecar_path: Path | None = None,
):
    registry, runtime, _definition = _knowledge_runtime()
    controller = PiSidecarController(
        tool_registry=registry,
        tool_runtime=runtime,
        sidecar_path=sidecar_path,
    )
    execution = recent_execution(run_id=run_id)
    context = ContextBuilderV1().build(execution)
    preparer = PiSkillDraftPreparer(
        controller=controller,
        script=tuple(script),
        max_context_chars=max_context_chars,
        observer=observer,
    )
    return execution, context, preparer


def test_detailed_tool_evidence_stays_ephemeral_and_public_result_is_body_free():
    registry, runtime, definition = _knowledge_runtime()
    controller = PiSidecarController(
        tool_registry=registry,
        tool_runtime=runtime,
    )

    detailed = controller.run_with_tool_records(
        _direct_request(
            definition,
            run_id="pi_detailed_evidence",
            script=(_tool_step(), _final_step()),
        )
    )

    assert detailed.result.status == "completed"
    assert len(detailed.tool_records) == 1
    record = detailed.tool_records[0]
    assert record.arguments == {"query": QUERY, "top_k": 2}
    assert record.result.success is True
    assert record.result.data is not None
    assert record.result.data["count"] == 2

    public_json = detailed.result.model_dump_json()
    assert QUERY not in public_json
    assert "01_metric_interpretation.md" not in public_json
    assert "chunks" not in public_json


def test_pi_draft_can_publish_only_through_existing_review_harness(tmp_path: Path):
    execution, context, preparer = _preparer(
        run_id="pi_harness_published",
        script=(_tool_step(), _final_step()),
    )
    evaluator = PassingEvaluator()
    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=evaluator,
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context)

    assert result.output.status == "published"
    assert result.output.report == _final_step().content
    assert result.output.evidence_source_ids
    assert result.output.evaluation_score == 95
    assert len(evaluator.requests) == 1
    assert result.agent_run is not None
    assert [message.role.value for message in result.agent_run.messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]

    final_records = [
        record
        for record in result.manifest.artifacts
        if record["kind"] == ArtifactKind.FINAL_REPORT.value
    ]
    assert len(final_records) == 1
    assert final_records[0]["producer"] == "review_harness.publisher"
    assert all("pi" not in record["producer"] for record in final_records)


def test_unknown_pi_citation_cannot_be_published(tmp_path: Path):
    execution, context, preparer = _preparer(
        run_id="pi_harness_bad_citation",
        script=(
            _tool_step(),
            _final_step("# Coach draft\n\n伪造引用 [K999]。"),
        ),
    )
    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=UnexpectedEvaluator(),
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context)

    assert result.output.status == "degraded"
    assert result.output.report == execution.typed_input.deterministic_report
    assert "draft_validation_failed" in result.output.warnings
    final_record = next(
        record
        for record in result.manifest.artifacts
        if record["kind"] == ArtifactKind.FINAL_REPORT.value
    )
    assert final_record["producer"] == "review_harness.deterministic_fallback"


def test_process_failure_degrades_without_inventing_agent_terminal(tmp_path: Path):
    execution, context, preparer = _preparer(
        run_id="pi_harness_process_failure",
        script=(_final_step(),),
        sidecar_path=tmp_path / "missing-sidecar.mjs",
    )
    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=UnexpectedEvaluator(),
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context)

    assert result.output.status == "degraded"
    assert result.output.warnings == (
        "deterministic_fallback",
        "draft_preparation_failed",
    )
    assert result.agent_failure is None
    assert preparer.last_execution is not None
    assert preparer.last_execution.result.stop_reason == "process_error"
    assert "missing-sidecar" not in repr(result.output)
    with pytest.raises(PiTraceParityError, match="unsupported_agent_terminal"):
        PiRuntimeSignalProjector().project(preparer.last_execution.result)


def test_failed_knowledge_tool_cannot_supply_harness_evidence(tmp_path: Path):
    registry, _runtime, definition = _knowledge_runtime()

    def fail_search(_params, _context):
        raise RuntimeError("raw Tool failure must not escape")

    failing_definition = ToolDefinition(
        name=definition.name,
        version=definition.version,
        description=definition.description,
        handler=fail_search,
        input_schema=definition.input_schema,
        output_schema=definition.output_schema,
        policy=definition.policy,
        idempotent=definition.idempotent,
    )
    failing_registry = ToolRegistry()
    failing_registry.register(failing_definition)
    controller = PiSidecarController(
        tool_registry=failing_registry,
        tool_runtime=ToolRuntime(failing_registry),
    )
    execution = recent_execution(run_id="pi_harness_tool_failure")
    context = ContextBuilderV1().build(execution)
    preparer = PiSkillDraftPreparer(
        controller=controller,
        script=(
            _tool_step(),
            _final_step("# Coach draft\n\nTool failure was ignored."),
        ),
        max_context_chars=200_000,
    )

    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=UnexpectedEvaluator(),
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context)

    assert result.output.status == "degraded"
    assert preparer.last_execution is not None
    projection = preparer.last_execution.result.tool_executions[0]
    assert projection.success is False
    assert projection.failure_code == "tool_execution_failed"
    assert "raw Tool failure" not in preparer.last_execution.result.model_dump_json()


def test_char_guard_is_not_claimed_as_token_unit_parity(tmp_path: Path):
    execution, context, preparer = _preparer(
        run_id="pi_harness_char_guard",
        script=(_final_step(),),
        max_context_chars=1,
    )
    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=UnexpectedEvaluator(),
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context)

    assert context.estimated_tokens <= context.max_context_tokens
    assert result.output.status == "degraded"
    assert preparer.last_execution is not None
    assert preparer.last_execution.result.stop_reason == "context_budget_exceeded"
    assert preparer.context_policy_parity == "approximate_char_guard"


def test_projector_refuses_pi_terminal_not_representable_by_runtime_contract():
    registry, runtime, definition = _knowledge_runtime()
    result = PiSidecarController(
        tool_registry=registry,
        tool_runtime=runtime,
    ).run(
        _direct_request(
            definition,
            run_id="pi_unrepresentable_abort",
            script=(
                PiScriptedFailureStep(
                    kind="provider_abort",
                    error_code="scripted_provider_abort",
                ),
            ),
        )
    )

    with pytest.raises(PiTraceParityError, match="unsupported_agent_terminal"):
        PiRuntimeSignalProjector().project(result)


def test_missing_usage_cannot_be_normalized_to_zero_or_published(tmp_path: Path):
    execution, context, preparer = _preparer(
        run_id="pi_harness_missing_usage",
        script=(
            PiScriptedAssistantStep(
                content="# Coach draft\n\nNo observed Usage.",
                usage=None,
            ),
        ),
    )
    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=UnexpectedEvaluator(),
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context)

    assert result.output.status == "degraded"
    assert preparer.last_execution is not None
    usage = preparer.last_execution.result.usage
    assert usage.token_observation.value == "unknown"
    assert usage.input_tokens is None
    assert usage.output_tokens is None


def test_provider_error_is_representable_by_current_runtime_terminal():
    registry, runtime, definition = _knowledge_runtime()
    controller = PiSidecarController(
        tool_registry=registry,
        tool_runtime=runtime,
    )
    provider_failure = controller.run(
        _direct_request(
            definition,
            run_id="pi_provider_failure_projection",
            script=(
                PiScriptedFailureStep(
                    kind="provider_error",
                    error_code="scripted_provider_error",
                ),
            ),
        )
    )
    signals = PiRuntimeSignalProjector().project(provider_failure)
    assert signals[-1].kind == "agent_run_terminated"
    assert signals[-1].stop_reason.value == "provider_error"


def test_successful_pi_harness_path_builds_existing_body_free_runtime_trace(
    tmp_path: Path,
):
    run_id = "pi_harness_runtime_trace"
    recorder = RuntimeRecorder(run_id=run_id, event_budget=256)
    observer = RecorderObserver(recorder)
    execution, context, preparer = _preparer(
        run_id=run_id,
        script=(_tool_step(), _final_step()),
        observer=observer,
    )
    manifest = execution.skill.manifest
    policy = RuntimePolicySnapshot(
        policy_version="1.0.0",
        event_budget=256,
        max_iterations=manifest.budgets.max_iterations,
        max_tool_calls=manifest.budgets.max_tool_calls,
        timeout_s=manifest.budgets.timeout_s,
        max_context_tokens=manifest.budgets.max_context_tokens,
        publish_score_threshold=manifest.quality_gate.minimum_score,
        max_revisions=1,
        allow_deterministic_fallback=(
            manifest.quality_gate.allow_deterministic_fallback
        ),
    )
    recorder.emit(
        RunStartedSignal(
            skill_name=manifest.name,
            skill_version=manifest.version,
            runtime_policy_version=policy.policy_version,
        )
    )
    recorder.emit(
        ExecutionValidatedSignal(
            input_artifact_sha256s=(
                execution.input_artifacts.player_summary.sha256,
                execution.input_artifacts.deterministic_report.sha256,
            )
        )
    )
    recorder.emit(
        ContextBuiltSignal(
            context_contract_version="1.0.0",
            estimated_context_units=context.estimated_tokens,
            omitted_item_ids=context.omitted_section_ids,
        )
    )

    result = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=preparer,
        evaluator=PassingEvaluator(),
        reviser=UnexpectedReviser(),
    ).execute(execution=execution, context=context, observer=observer)
    terminal_reason = result.manifest.transitions[-1]["reason"]
    publication = RuntimePublicationStatus(result.output.status)
    recorder.emit(
        RunCompletedSignal(
            publication_status=publication,
            terminal_reason=terminal_reason,
        )
    )

    store = FileRunStore(tmp_path, run_id)
    trace = recorder.build_trace(
        identity=RuntimeIdentitySnapshot(
            skill_name=manifest.name,
            skill_version=manifest.version,
            context_contract_version="1.0.0",
            prompt_profile_id="pi-evaluation",
            prompt_profile_version="1.0.0",
            provider_id="riftcoach-scripted",
            provider_model="riftcoach-scripted-model",
            harness_version="1.0.0",
        ),
        policy=policy,
        artifacts=project_artifact_references(
            manifest=result.manifest,
            store=store,
        ),
    )

    assert preparer.last_execution is not None
    assert trace.usage == preparer.last_execution.result.usage
    assert trace.publication_status is RuntimePublicationStatus.PUBLISHED
    provider_finishes = [
        event.signal.finish_reason.value
        for event in trace.events
        if event.signal.kind == "provider_call_completed"
    ]
    assert provider_finishes == ["tool_calls", "stop"]
    assert trace.artifacts
    safe_trace = trace.model_dump_json()
    assert QUERY not in safe_trace
    assert "chunks" not in safe_trace
    assert "谨慎训练建议" not in safe_trace
