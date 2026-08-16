from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.agent.context import ContextBuilderV1
from app.agent.draft import SkillAgentDraftPreparer
from app.harness.models import ArtifactKind, HarnessConfig, RunStatus
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    CoachDraft,
    DraftPreparationResult,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    KnowledgeCitation,
    KnowledgeEvidence,
)
from app.harness.store import ArtifactIntegrityError, FileRunStore
from app.runtime.artifacts import project_artifact_references
from app.runtime.observer import RuntimeObservationError
from app.runtime.signals import (
    EvaluationCompletedSignal,
    HarnessTransitionedSignal,
    PublicationDecidedSignal,
    RuntimePublicationStatus,
)
from app.skills.review_executor import SkillReviewExecutor
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tools.adapters import build_knowledge_tools
from app.tools.registry import ToolRegistry
from tests.test_skill_review_executor import (
    UnexpectedReviser,
    evidence,
    validated_recent,
)


class FixedPreparer:
    def prepare(self, request) -> DraftPreparationResult:
        return DraftPreparationResult(
            draft=CoachDraft(report="# Coach\n\n建议谨慎复盘 [K1]。\n"),
            knowledge=evidence(),
        )


class SequenceEvaluator:
    def __init__(self, results):
        self.results = list(results)

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FixedReviser:
    def revise(self, request) -> CoachDraft:
        return CoachDraft(report="# Coach\n\n修订后的建议 [K1]。\n")


class RecordingObserver:
    def __init__(self) -> None:
        self.signals = []

    def observe(self, signal) -> None:
        self.signals.append(signal)


class FailingObserver(RecordingObserver):
    def __init__(self, signal_type: type) -> None:
        super().__init__()
        self.signal_type = signal_type

    def observe(self, signal) -> None:
        if isinstance(signal, self.signal_type):
            raise RuntimeError("private observer failure")
        super().observe(signal)


class EvaluationArtifactFailureStore(FileRunStore):
    def write_artifact(self, *, kind, relative_path, content, schema_version, producer):
        if kind is ArtifactKind.EVALUATION_RESULT:
            raise OSError("private artifact write failure")
        return super().write_artifact(
            kind=kind,
            relative_path=relative_path,
            content=content,
            schema_version=schema_version,
            producer=producer,
        )


def _harness(store, *, evaluator=None, config=None, observer=None):
    return ReviewHarness(
        store=store,
        draft_preparer=FixedPreparer(),
        evaluator=evaluator or SequenceEvaluator(
            [EvaluationResult(score=92, verdict=EvaluationVerdict.PASS)]
        ),
        reviser=FixedReviser(),
        config=config or HarnessConfig(),
        observer=observer,
    )


def _run(harness):
    return harness.run(
        player_summary={"schema_version": "1.0", "games": 1},
        deterministic_report="# Deterministic\n",
    )


def test_harness_observes_only_persisted_transitions_evaluations_and_publication(
    tmp_path,
):
    run_id = "harness_observation_success"
    store = FileRunStore(tmp_path, run_id)
    observer = RecordingObserver()
    manifest = _run(
        _harness(
            store,
            evaluator=SequenceEvaluator(
                [
                    EvaluationResult(
                        score=72,
                        verdict=EvaluationVerdict.NEEDS_REVISION,
                        issues=(
                            {"category": "causality", "quote": "private"},
                        ),
                    ),
                    EvaluationResult(score=94, verdict=EvaluationVerdict.PASS),
                ]
            ),
            observer=observer,
        )
    )

    transitions = [
        signal for signal in observer.signals if isinstance(signal, HarnessTransitionedSignal)
    ]
    assert [(s.from_status.value, s.to_status.value, s.revision_count) for s in transitions] == [
        ("created", "facts_ready", 0),
        ("facts_ready", "knowledge_ready", 0),
        ("knowledge_ready", "draft_ready", 0),
        ("draft_ready", "evaluating", 0),
        ("evaluating", "needs_revision", 0),
        ("needs_revision", "revising", 1),
        ("revising", "re_evaluating", 1),
        ("re_evaluating", "passed", 1),
        ("passed", "published", 1),
    ]
    evaluations = [
        signal for signal in observer.signals if isinstance(signal, EvaluationCompletedSignal)
    ]
    assert [signal.attempt for signal in evaluations] == [0, 1]
    assert evaluations[0].blocking_categories == ()

    final_record = next(
        record for record in manifest.artifacts if record["kind"] == ArtifactKind.FINAL_REPORT.value
    )
    publications = [
        signal for signal in observer.signals if isinstance(signal, PublicationDecidedSignal)
    ]
    assert len(publications) == 1
    assert publications[0].publication_status is RuntimePublicationStatus.PUBLISHED
    assert publications[0].artifact_sha256s == (final_record["sha256"],)
    assert store.read_artifact(final_record) == (tmp_path / run_id / final_record["path"]).read_bytes()


def test_blocking_category_is_projected_without_issue_text(tmp_path):
    store = FileRunStore(tmp_path, "harness_observation_blocked")
    observer = RecordingObserver()
    manifest = _run(
        _harness(
            store,
            evaluator=SequenceEvaluator(
                [
                    EvaluationResult(
                        score=99,
                        verdict=EvaluationVerdict.NEEDS_REVISION,
                        issues=(
                            {"category": "prompt_injection", "quote": "secret"},
                            {"category": "causality", "quote": "private"},
                        ),
                    )
                ]
            ),
            observer=observer,
        )
    )
    evaluation = next(
        signal for signal in observer.signals if isinstance(signal, EvaluationCompletedSignal)
    )
    assert manifest.status is RunStatus.DEGRADED
    assert evaluation.blocking_categories == ("prompt_injection",)
    assert "secret" not in repr(evaluation)


def test_rejected_publication_never_projects_a_final_report(tmp_path):
    store = FileRunStore(tmp_path, "harness_observation_rejected")
    observer = RecordingObserver()
    manifest = _run(
        _harness(
            store,
            evaluator=SequenceEvaluator([RuntimeError("private evaluator error")]),
            config=HarnessConfig(allow_deterministic_fallback=False),
            observer=observer,
        )
    )

    publication = next(
        signal for signal in observer.signals if isinstance(signal, PublicationDecidedSignal)
    )
    assert manifest.status is RunStatus.REJECTED
    assert publication.publication_status is RuntimePublicationStatus.REJECTED
    assert publication.artifact_sha256s == ()
    assert not any(record["kind"] == ArtifactKind.FINAL_REPORT.value for record in manifest.artifacts)


def test_evaluation_artifact_must_be_persisted_before_completed_signal(tmp_path):
    store = EvaluationArtifactFailureStore(tmp_path, "harness_observation_artifact_failure")
    observer = RecordingObserver()

    with pytest.raises(OSError, match="artifact write"):
        _run(_harness(store, observer=observer))

    assert not any(isinstance(signal, EvaluationCompletedSignal) for signal in observer.signals)


def test_runtime_observation_failure_is_not_converted_to_deterministic_fallback(tmp_path):
    store = FileRunStore(tmp_path, "harness_observation_failure")
    observer = FailingObserver(EvaluationCompletedSignal)

    with pytest.raises(RuntimeObservationError):
        _run(_harness(store, observer=observer))

    manifest = store.read_manifest()
    assert manifest.status is RunStatus.EVALUATING
    assert not any(record["kind"] == ArtifactKind.FINAL_REPORT.value for record in manifest.artifacts)


def test_skill_review_executor_exposes_the_same_observer_port(tmp_path):
    execution = validated_recent("executor_observer_port")
    context = ContextBuilderV1().build(execution)
    observer = RecordingObserver()
    executor = SkillReviewExecutor(
        runs_root=tmp_path,
        draft_preparer=__import__(
            "tests.test_skill_review_executor",
            fromlist=["FakeSkillAgentPreparer"],
        ).FakeSkillAgentPreparer(),
        evaluator=SequenceEvaluator([EvaluationResult(score=92, verdict=EvaluationVerdict.PASS)]),
        reviser=UnexpectedReviser(),
    )

    result = executor.execute(execution=execution, context=context, observer=observer)

    assert result.output.status == "published"
    assert any(isinstance(signal, PublicationDecidedSignal) for signal in observer.signals)


def test_artifact_projection_revalidates_real_bytes_and_returns_safe_references(tmp_path):
    store = FileRunStore(tmp_path, "artifact_projection")
    manifest = _run(_harness(store))

    references = project_artifact_references(manifest=manifest, store=store)
    final_record = next(
        record for record in manifest.artifacts if record["kind"] == ArtifactKind.FINAL_REPORT.value
    )
    final_reference = next(reference for reference in references if reference.kind == "final_report")
    assert final_reference.relative_path == final_record["path"]
    assert final_reference.sha256 == hashlib.sha256(store.read_artifact(final_record)).hexdigest()
    assert "Coach" not in repr(references)

    (store.run_directory / final_record["path"]).write_text("tampered", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        project_artifact_references(manifest=store.read_manifest(), store=store)


def test_agent_draft_preparer_does_not_wrap_runtime_observation_failure():
    registry = ToolRegistry()
    registry.register(
        build_knowledge_tools(
            LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))
        )[0]
    )

    class RaisingAgentLoop:
        tool_registry = registry

        def run(self, request):
            raise RuntimeObservationError("observer failed")

    execution = validated_recent("draft_observer_failure")
    context = ContextBuilderV1().build(execution)
    with pytest.raises(RuntimeObservationError):
        SkillAgentDraftPreparer(RaisingAgentLoop()).prepare(execution, context)
