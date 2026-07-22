import json
import tempfile
import unittest
from pathlib import Path

from app.harness.models import ArtifactKind, HarnessConfig, RunStatus
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    CoachDraft,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    GenerationRequest,
    KnowledgeEvidence,
    RetrievalRequest,
    RevisionRequest,
)
from app.harness.store import FileRunStore


class FakeRetriever:
    def __init__(self) -> None:
        self.requests: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> KnowledgeEvidence:
        self.requests.append(request)
        return KnowledgeEvidence(
            context="视野分只能作为复盘线索，不能单独证明因果。",
            source_ids=("review-rules-v1",),
        )


class FakeGenerator:
    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    def generate(self, request: GenerationRequest) -> CoachDraft:
        self.requests.append(request)
        return CoachDraft(
            report="# RiftCoach 教练式复盘报告\n\n当前数据支持谨慎复盘。\n"
        )


class PassingEvaluator:
    def __init__(self) -> None:
        self.requests: list[EvaluationRequest] = []

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        self.requests.append(request)
        return EvaluationResult(
            score=92,
            verdict=EvaluationVerdict.PASS,
            issues=(),
            passed_checks=("数字忠实", "因果边界"),
            summary="报告可以发布。",
        )


class UnexpectedReviser:
    def __init__(self) -> None:
        self.requests: list[RevisionRequest] = []

    def revise(self, request: RevisionRequest) -> CoachDraft:
        self.requests.append(request)
        raise AssertionError("The passing path must not call the reviser.")


class ReviewHarnessPassingPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.runs_root = Path(self.temporary_directory.name)
        self.run_id = "review_passing_example"
        self.store = FileRunStore(self.runs_root, self.run_id)
        self.retriever = FakeRetriever()
        self.generator = FakeGenerator()
        self.evaluator = PassingEvaluator()
        self.reviser = UnexpectedReviser()
        self.harness = ReviewHarness(
            store=self.store,
            retriever=self.retriever,
            generator=self.generator,
            evaluator=self.evaluator,
            reviser=self.reviser,
            config=HarnessConfig(publish_score_threshold=85),
        )
        self.player_summary = {
            "schema_version": "1.0",
            "player": {"riot_id": "Example#TEST"},
            "recent_summary": {"games_analyzed": 2},
        }
        self.deterministic_report = "# RiftCoach 确定性报告\n\n分析场次：2 局。\n"

    def test_first_evaluation_passes_and_publishes_the_coach_report(self) -> None:
        manifest = self.harness.run(
            player_summary=self.player_summary,
            deterministic_report=self.deterministic_report,
        )

        self.assertEqual(RunStatus.PUBLISHED, manifest.status)
        self.assertEqual("published", manifest.final_decision)
        self.assertEqual(0, manifest.revision_count)
        self.assertEqual([], self.reviser.requests)

        transition_targets = [row["to"] for row in manifest.transitions]
        self.assertEqual(
            [
                "facts_ready",
                "knowledge_ready",
                "draft_ready",
                "evaluating",
                "passed",
                "published",
            ],
            transition_targets,
        )

        records_by_kind = {row["kind"]: row for row in manifest.artifacts}
        expected_kinds = {kind.value for kind in ArtifactKind} - {
            ArtifactKind.REVISED_REPORT.value,
            ArtifactKind.RUN_MANIFEST.value,
        }
        self.assertEqual(expected_kinds, set(records_by_kind))

        draft_record = records_by_kind[ArtifactKind.COACH_DRAFT.value]
        final_record = records_by_kind[ArtifactKind.FINAL_REPORT.value]
        self.assertEqual(draft_record["sha256"], final_record["sha256"])
        self.assertNotEqual(draft_record["artifact_id"], final_record["artifact_id"])
        self.assertEqual(
            self.store.read_artifact(draft_record),
            self.store.read_artifact(final_record),
        )

        evaluation_record = records_by_kind[ArtifactKind.EVALUATION_RESULT.value]
        evaluation_payload = json.loads(
            self.store.read_artifact(evaluation_record).decode("utf-8")
        )
        self.assertEqual(92, evaluation_payload["score"])
        self.assertEqual("pass", evaluation_payload["verdict"])

        self.assertEqual(1, len(self.retriever.requests))
        self.assertEqual(1, len(self.generator.requests))
        self.assertEqual(1, len(self.evaluator.requests))
        self.assertEqual(
            ("review-rules-v1",),
            self.generator.requests[0].knowledge.source_ids,
        )
        self.assertEqual(
            self.generator.requests[0].knowledge,
            self.evaluator.requests[0].knowledge,
        )


if __name__ == "__main__":
    unittest.main()
