from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.agent.context import ContextBuilderV1
from app.agent.draft import (
    AgentDraftPreparationError,
    AgentDraftPreparationResult,
    SkillAgentDraftPreparer,
)
from app.agent.loop import AgentLoop, AgentRunResult, AgentRunStatus, AgentStopReason
from app.harness.models import ArtifactKind, HarnessConfig
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    CoachDraft,
    DraftPreparationResult,
    EvaluationResult,
    EvaluationVerdict,
    KnowledgeCitation,
    KnowledgeEvidence,
)
from app.harness.store import FileRunStore
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
    ValidatedSkillExecution,
)
from app.skills.recent_form_review import RecentFormReviewOutput
from app.skills.review_executor import (
    SkillReviewExecutionResult,
    SkillReviewExecutionError,
    SkillReviewExecutor,
    SkillTerminalOutputBuilder,
)
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.skills.single_match_review import SingleMatchReviewOutput
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tools.adapters import build_knowledge_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from app.providers.models import ChatResponse, TokenUsage
from tests.test_agent_draft_preparer import (
    KnowledgeSeekingProvider,
    demo_report,
    demo_summary,
    validated_execution,
)


def valid_summary() -> dict:
    return {
        "schema_version": "1.0",
        "metadata": {},
        "player": {
            "game_name": "DemoPlayer",
            "tag_line": "TEST",
            "riot_id": "DemoPlayer#TEST",
        },
        "request": {"count": 10},
        "recent_summary": {"games_analyzed": 1},
        "matches": [
            {
                "match_id": "KR_1",
                "game_duration_seconds": 1800,
                "champion_id": 103,
                "champion_name": "Ahri",
                "role": "MIDDLE",
                "win": True,
                "timeline_status": "available",
                "included_in_aggregate": True,
            }
        ],
        "failed_matches": [],
        "excluded_matches": [],
    }


def validated_recent(run_id: str) -> ValidatedSkillExecution:
    catalog = SkillCatalog.from_directory("skills")
    utterance = "分析我最近十局的状态"
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    payload = {
        "player_summary": valid_summary(),
        "deterministic_report": "# 确定性报告\n\n只包含可验证事实。\n",
        "focus": "survival",
    }
    assert decision.selected_skill is not None
    skill = catalog.get(decision.selected_skill)
    assert skill is not None
    typed_input = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    return SkillExecutionBoundary(catalog).validate(
        SkillExecutionRequest(
            run_id=run_id,
            user_utterance=utterance,
            router_decision=decision,
            input_payload=payload,
            input_artifacts=binding,
        )
    )


def evidence() -> KnowledgeEvidence:
    return KnowledgeEvidence(
        context="训练建议只能基于可验证数据。",
        source_ids=("review-rules.md",),
        citations=(
            KnowledgeCitation(
                citation_id="K1",
                chunk_id="review-rules.md:child:1",
                parent_id="review-rules.md:parent:1",
                source_id="review-rules.md",
                title="复盘规则",
                content="训练建议只能基于可验证数据。",
            ),
        ),
    )


class FixedPreparer:
    def __init__(self, report: str = "# Coach\n\n谨慎建议 [K1]。\n") -> None:
        self.report = report

    def prepare(self, request) -> DraftPreparationResult:
        return DraftPreparationResult(
            draft=CoachDraft(report=self.report),
            knowledge=evidence(),
        )


class RaisingPreparer:
    def prepare(self, request):
        raise RuntimeError("raw preparation details")


class SequenceEvaluator:
    def __init__(self, results):
        self.results = list(results)
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FixedReviser:
    def __init__(self, report: str) -> None:
        self.report = report

    def revise(self, request) -> CoachDraft:
        return CoachDraft(report=self.report)


class UnexpectedReviser:
    def revise(self, request):
        raise AssertionError("reviser should not run")


def completed_agent_run(report: str) -> AgentRunResult:
    response = ChatResponse(
        content=report,
        model="fake-model",
        provider="fake-provider",
        usage=TokenUsage(input_tokens=10, output_tokens=20),
    )
    return AgentRunResult(
        status=AgentRunStatus.COMPLETED,
        stop_reason=AgentStopReason.FINAL_RESPONSE,
        messages=(),
        provider_responses=(response,),
        tool_executions=(),
        usage=response.usage,
        iterations=1,
        final_response=response,
    )


class FakeSkillAgentPreparer:
    def __init__(self, report: str = "# Coach\n\nAgent 草稿 [K1]。\n") -> None:
        self.report = report
        self.requests = []
        self.agent_run = completed_agent_run(report)

    def prepare(self, execution, context) -> AgentDraftPreparationResult:
        self.requests.append((execution, context))
        return AgentDraftPreparationResult(
            draft=CoachDraft(report=self.report),
            knowledge=evidence(),
            agent_run=self.agent_run,
        )


class FailingSkillAgentPreparer:
    def prepare(self, execution, context):
        raise AgentDraftPreparationError("secret provider payload")


def run_harness(
    root: Path,
    execution: ValidatedSkillExecution,
    *,
    preparer=None,
    evaluator=None,
    reviser=None,
    config=None,
) -> FileRunStore:
    typed_input = execution.typed_input
    store = FileRunStore(root, execution.run_id)
    harness = ReviewHarness(
        store=store,
        draft_preparer=preparer or FixedPreparer(),
        evaluator=evaluator
        or SequenceEvaluator(
            [
                EvaluationResult(
                    score=92,
                    verdict=EvaluationVerdict.PASS,
                )
            ]
        ),
        reviser=reviser or UnexpectedReviser(),
        config=config or HarnessConfig(),
    )
    harness.run(
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    return store


def test_builder_creates_typed_published_output_from_persisted_artifacts():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_published")
        store = run_harness(Path(directory), execution)

        output = SkillTerminalOutputBuilder().build(
            execution=execution,
            store=store,
        )

        assert isinstance(output, RecentFormReviewOutput)
        assert output.run_id == execution.run_id
        assert output.status == "published"
        assert output.report == "# Coach\n\n谨慎建议 [K1]。"
        assert output.evaluation_score == 92
        assert output.evidence_source_ids == ("review-rules.md",)
        assert output.warnings == ()


def test_builder_uses_final_revision_and_final_attempt_evaluation():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_revised")
        revised_report = "# Coach\n\n修订后的谨慎建议 [K1]。\n"
        store = run_harness(
            Path(directory),
            execution,
            evaluator=SequenceEvaluator(
                [
                    EvaluationResult(
                        score=70,
                        verdict=EvaluationVerdict.NEEDS_REVISION,
                        issues=({"category": "fact_error"},),
                    ),
                    EvaluationResult(
                        score=91,
                        verdict=EvaluationVerdict.PASS,
                    ),
                ]
            ),
            reviser=FixedReviser(revised_report),
        )

        output = SkillTerminalOutputBuilder().build(
            execution=execution,
            store=store,
        )

        assert output.status == "published"
        assert output.report == revised_report.strip()
        assert output.evaluation_score == 91


def test_builder_reports_deterministic_degradation_without_inventing_score():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_degraded")
        store = run_harness(
            Path(directory),
            execution,
            evaluator=SequenceEvaluator([RuntimeError("raw evaluator error")]),
        )

        output = SkillTerminalOutputBuilder().build(
            execution=execution,
            store=store,
        )

        assert output.status == "degraded"
        assert output.report == execution.typed_input.deterministic_report
        assert output.evaluation_score is None
        assert output.evidence_source_ids == ("review-rules.md",)
        assert output.warnings == (
            "deterministic_fallback",
            "evaluation_failed",
        )
        assert "raw evaluator error" not in " ".join(output.warnings)


def test_builder_rejected_output_never_exposes_a_report():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_rejected")
        store = run_harness(
            Path(directory),
            execution,
            preparer=RaisingPreparer(),
            config=HarnessConfig(allow_deterministic_fallback=False),
        )

        output = SkillTerminalOutputBuilder().build(
            execution=execution,
            store=store,
        )

        assert output.status == "rejected"
        assert output.report is None
        assert output.evaluation_score is None
        assert output.evidence_source_ids == ()
        assert output.warnings == (
            "report_rejected",
            "draft_preparation_failed",
        )


def test_builder_rejects_input_commitment_drift():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_binding_drift")
        store = run_harness(Path(directory), execution)
        wrong_commitment = execution.input_artifacts.player_summary.model_copy(
            update={"sha256": "0" * 64}
        )
        drifted = replace(
            execution,
            input_artifacts=execution.input_artifacts.model_copy(
                update={"player_summary": wrong_commitment}
            ),
        )

        with pytest.raises(SkillReviewExecutionError, match="commitment"):
            SkillTerminalOutputBuilder().build(
                execution=drifted,
                store=store,
            )


def test_builder_rejects_tampered_terminal_artifact():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_tampered")
        store = run_harness(Path(directory), execution)
        manifest = store.read_manifest()
        evidence_record = next(
            record
            for record in manifest.artifacts
            if record["kind"] == ArtifactKind.RETRIEVAL_EVIDENCE.value
        )
        (store.run_directory / evidence_record["path"]).write_text(
            '{"source_ids": ["forged.md"]}\n',
            encoding="utf-8",
        )

        with pytest.raises(SkillReviewExecutionError, match="terminal artifact"):
            SkillTerminalOutputBuilder().build(
                execution=execution,
                store=store,
            )


class ImpossibleOutput(BaseModel):
    impossible_required_field: str


def test_builder_fails_closed_when_declared_output_model_rejects_payload():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_terminal_output_contract")
        store = run_harness(Path(directory), execution)
        drifted = replace(
            execution,
            skill=replace(execution.skill, output_model=ImpossibleOutput),
        )

        with pytest.raises(SkillReviewExecutionError, match="output validation"):
            SkillTerminalOutputBuilder().build(
                execution=drifted,
                store=store,
            )


def test_executor_maps_manifest_threshold_and_preserves_agent_run():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_executor_threshold")
        context = ContextBuilderV1().build(execution)
        preparer = FakeSkillAgentPreparer()
        evaluator = SequenceEvaluator(
            [
                EvaluationResult(
                    score=84,
                    verdict=EvaluationVerdict.PASS,
                )
            ]
        )
        executor = SkillReviewExecutor(
            runs_root=Path(directory),
            draft_preparer=preparer,
            evaluator=evaluator,
            reviser=UnexpectedReviser(),
        )

        result = executor.execute(execution=execution, context=context)

        assert isinstance(result, SkillReviewExecutionResult)
        assert result.output.status == "degraded"
        assert result.output.evaluation_score == 84
        assert result.manifest.config.publish_score_threshold == 85
        assert result.manifest.config.allow_deterministic_fallback is True
        assert result.agent_run is preparer.agent_run
        assert len(evaluator.requests) == 1


def test_executor_routes_agent_preparation_failure_through_harness_fallback():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_executor_prepare_failure")
        context = ContextBuilderV1().build(execution)
        evaluator = SequenceEvaluator([])
        executor = SkillReviewExecutor(
            runs_root=Path(directory),
            draft_preparer=FailingSkillAgentPreparer(),
            evaluator=evaluator,
            reviser=UnexpectedReviser(),
        )

        result = executor.execute(execution=execution, context=context)

        assert result.output.status == "degraded"
        assert result.output.report == execution.typed_input.deterministic_report
        assert result.output.warnings == (
            "deterministic_fallback",
            "draft_preparation_failed",
        )
        assert result.agent_run is None
        assert evaluator.requests == []
        assert "secret provider payload" not in " ".join(result.output.warnings)


def test_executor_rejects_context_identity_drift_before_creating_run():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        execution = validated_recent("review_executor_context_drift")
        context = replace(
            ContextBuilderV1().build(execution),
            skill_version="9.9.9",
        )
        executor = SkillReviewExecutor(
            runs_root=root,
            draft_preparer=FakeSkillAgentPreparer(),
            evaluator=SequenceEvaluator([]),
            reviser=UnexpectedReviser(),
        )

        with pytest.raises(SkillReviewExecutionError, match="context identity"):
            executor.execute(execution=execution, context=context)

        assert list(root.iterdir()) == []


def test_executor_uses_manifest_rejection_policy_without_caller_override():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_executor_rejected")
        gate = execution.skill.manifest.quality_gate.model_copy(
            update={"allow_deterministic_fallback": False}
        )
        manifest = execution.skill.manifest.model_copy(
            update={"quality_gate": gate}
        )
        execution = replace(
            execution,
            skill=replace(execution.skill, manifest=manifest),
        )
        context = ContextBuilderV1().build(execution)
        executor = SkillReviewExecutor(
            runs_root=Path(directory),
            draft_preparer=FailingSkillAgentPreparer(),
            evaluator=SequenceEvaluator([]),
            reviser=UnexpectedReviser(),
        )

        result = executor.execute(execution=execution, context=context)

        assert result.output.status == "rejected"
        assert result.output.report is None
        assert result.manifest.config.allow_deterministic_fallback is False


def test_executor_publishes_only_the_harness_revision_and_final_score():
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_recent("review_executor_revised")
        context = ContextBuilderV1().build(execution)
        preparer = FakeSkillAgentPreparer("# Coach\n\n原始 Agent 草稿 [K1]。\n")
        revised_report = "# Coach\n\n通过事实审查的修订稿 [K1]。\n"
        evaluator = SequenceEvaluator(
            [
                EvaluationResult(
                    score=70,
                    verdict=EvaluationVerdict.NEEDS_REVISION,
                    issues=({"category": "fact_error"},),
                ),
                EvaluationResult(
                    score=93,
                    verdict=EvaluationVerdict.PASS,
                ),
            ]
        )
        executor = SkillReviewExecutor(
            runs_root=Path(directory),
            draft_preparer=preparer,
            evaluator=evaluator,
            reviser=FixedReviser(revised_report),
        )

        result = executor.execute(execution=execution, context=context)

        assert result.output.status == "published"
        assert result.output.report == revised_report.strip()
        assert result.output.report != preparer.report.strip()
        assert result.output.evaluation_score == 93
        assert len(evaluator.requests) == 2


def test_executor_rejects_a_disabled_quality_gate_before_creating_run():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        execution = validated_recent("review_executor_gate_disabled")
        disabled_gate = execution.skill.manifest.quality_gate.model_validate(
            {
                "required": False,
                "minimum_score": 0,
                "allow_deterministic_fallback": True,
            }
        )
        execution = replace(
            execution,
            skill=replace(
                execution.skill,
                manifest=execution.skill.manifest.model_copy(
                    update={"quality_gate": disabled_gate}
                ),
            ),
        )
        context = ContextBuilderV1().build(execution)
        executor = SkillReviewExecutor(
            runs_root=root,
            draft_preparer=FakeSkillAgentPreparer(),
            evaluator=SequenceEvaluator([]),
            reviser=UnexpectedReviser(),
        )

        with pytest.raises(SkillReviewExecutionError, match="quality gate"):
            executor.execute(execution=execution, context=context)

        assert list(root.iterdir()) == []


@pytest.mark.parametrize(
    (
        "utterance",
        "payload",
        "run_id",
        "expected_skill",
        "expected_output_type",
        "expected_target_match_id",
    ),
    (
        (
            "分析我最近十局的状态",
            {
                "player_summary": demo_summary(),
                "deterministic_report": demo_report(),
                "focus": "survival",
            },
            "review_full_recent_real_rag",
            "recent-form-review",
            RecentFormReviewOutput,
            None,
        ),
        (
            "深入复盘这一场的表现",
            {
                "player_summary": demo_summary(),
                "deterministic_report": demo_report(),
                "target_match_id": "SYNTHETIC_WIN_001",
                "focus": "laning",
            },
            "review_full_single_real_rag",
            "single-match-review",
            SingleMatchReviewOutput,
            "SYNTHETIC_WIN_001",
        ),
    ),
)
def test_both_real_skills_reach_typed_terminal_output_through_one_harness(
    utterance: str,
    payload: dict,
    run_id: str,
    expected_skill: str,
    expected_output_type: type[BaseModel],
    expected_target_match_id: str | None,
):
    with tempfile.TemporaryDirectory() as directory:
        execution = validated_execution(
            utterance=utterance,
            payload=payload,
            run_id=run_id,
        )
        context = ContextBuilderV1().build(execution)
        registry = ToolRegistry()
        for definition in build_knowledge_tools(
            LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))
        ):
            registry.register(definition)
        provider = KnowledgeSeekingProvider()
        loop = AgentLoop(
            provider=provider,
            tool_registry=registry,
            tool_runtime=ToolRuntime(
                registry,
                call_id_factory=lambda: "full-review-knowledge-call",
            ),
        )
        evaluator = SequenceEvaluator(
            [
                EvaluationResult(
                    score=94,
                    verdict=EvaluationVerdict.PASS,
                )
            ]
        )
        executor = SkillReviewExecutor(
            runs_root=Path(directory),
            draft_preparer=SkillAgentDraftPreparer(loop),
            evaluator=evaluator,
            reviser=UnexpectedReviser(),
        )

        result = executor.execute(execution=execution, context=context)

        assert execution.skill.manifest.name == expected_skill
        assert isinstance(result.output, expected_output_type)
        assert result.output.status == "published"
        assert result.output.evaluation_score == 94
        assert result.output.evidence_source_ids
        assert "ghost-only.md" in result.output.report
        assert "ghost-only.md" not in result.output.evidence_source_ids
        assert result.manifest.config.publish_score_threshold == (
            execution.skill.manifest.quality_gate.minimum_score
        )
        assert result.agent_run is not None
        assert result.agent_run.status is AgentRunStatus.COMPLETED
        assert len(result.agent_run.tool_executions) == 1
        assert result.agent_run.tool_executions[0].tool_name == "knowledge.search"
        assert evaluator.requests[0].report == result.output.report
        assert provider.provider_name == "fake-knowledge-agent"
        assert len(provider.requests) == 2
        if expected_target_match_id is not None:
            assert result.output.target_match_id == expected_target_match_id
