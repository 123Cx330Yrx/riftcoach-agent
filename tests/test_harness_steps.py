import unittest

from app.harness.adapters import SequentialDraftPreparer
from app.harness.steps import (
    CoachDraft,
    DraftPreparationRequest,
    DraftPreparationResult,
    DraftPreparationStep,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    EvaluatorStep,
    GenerationRequest,
    GeneratorStep,
    KnowledgeEvidence,
    RetrievalRequest,
    RetrieverStep,
    RevisionRequest,
    ReviserStep,
)


class FakeRetriever:
    def retrieve(self, request: RetrievalRequest) -> KnowledgeEvidence:
        return KnowledgeEvidence(
            context="补刀/分钟用于描述发育效率。",
            source_ids=("metric-guide-v1",),
        )


class FakeGenerator:
    def generate(self, request: GenerationRequest) -> CoachDraft:
        return CoachDraft(report="# RiftCoach 教练式复盘报告\n草稿")


class FakeEvaluator:
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        return EvaluationResult(
            score=82,
            verdict=EvaluationVerdict.NEEDS_REVISION,
            issues=(
                {
                    "category": "causality",
                    "explanation": "相关性不能证明因果。",
                },
            ),
        )


class FakeReviser:
    def revise(self, request: RevisionRequest) -> CoachDraft:
        return CoachDraft(report=request.report.replace("导致", "可能相关"))


class HarnessStepContractTests(unittest.TestCase):
    def setUp(self):
        self.retrieval_request = RetrievalRequest(
            player_summary={"player": {"riot_id": "Example#TEST"}},
            deterministic_report="# 确定性报告",
        )

    def test_fake_steps_satisfy_runtime_checkable_protocols(self):
        self.assertIsInstance(FakeRetriever(), RetrieverStep)
        self.assertIsInstance(FakeGenerator(), GeneratorStep)
        self.assertIsInstance(FakeEvaluator(), EvaluatorStep)
        self.assertIsInstance(FakeReviser(), ReviserStep)

    def test_sequential_adapter_satisfies_unified_preparation_contract(self):
        retriever = FakeRetriever()
        generator = FakeGenerator()
        preparer = SequentialDraftPreparer(
            retriever=retriever,
            generator=generator,
        )
        request = DraftPreparationRequest(
            player_summary=self.retrieval_request.player_summary,
            deterministic_report=self.retrieval_request.deterministic_report,
        )

        result = preparer.prepare(request)

        self.assertIsInstance(preparer, DraftPreparationStep)
        self.assertIsInstance(result, DraftPreparationResult)
        self.assertEqual("metric-guide-v1", result.knowledge.source_ids[0])
        self.assertTrue(result.draft.report.startswith("# RiftCoach"))

    def test_preparation_result_rejects_wrong_contract_values(self):
        with self.assertRaises(TypeError):
            DraftPreparationResult(
                draft="not-a-draft",  # type: ignore[arg-type]
                knowledge=KnowledgeEvidence.empty(),
            )

        with self.assertRaises(TypeError):
            DraftPreparationResult(
                draft=CoachDraft(report="valid"),
                knowledge={},  # type: ignore[arg-type]
            )

    def test_retrieval_contract_returns_context_and_source_ids(self):
        result = FakeRetriever().retrieve(self.retrieval_request)

        self.assertIn("发育效率", result.context)
        self.assertEqual(("metric-guide-v1",), result.source_ids)

    def test_generation_contract_receives_facts_and_retrieval_evidence(self):
        evidence = FakeRetriever().retrieve(self.retrieval_request)
        request = GenerationRequest(
            player_summary=self.retrieval_request.player_summary,
            deterministic_report=self.retrieval_request.deterministic_report,
            knowledge=evidence,
        )

        draft = FakeGenerator().generate(request)

        self.assertTrue(draft.report.startswith("# RiftCoach"))
        self.assertEqual(("metric-guide-v1",), request.knowledge.source_ids)

    def test_evaluation_contract_has_bounded_score_and_verdict(self):
        result = FakeEvaluator().evaluate(
            EvaluationRequest(
                player_summary=self.retrieval_request.player_summary,
                deterministic_report=self.retrieval_request.deterministic_report,
                knowledge=KnowledgeEvidence.empty(),
                report="# RiftCoach 教练式复盘报告\n导致",
            )
        )

        self.assertEqual(82, result.score)
        self.assertEqual(EvaluationVerdict.NEEDS_REVISION, result.verdict)
        self.assertEqual("causality", result.issues[0]["category"])

        with self.assertRaises(ValueError):
            EvaluationResult(
                score=101,
                verdict=EvaluationVerdict.FAIL,
            )

        with self.assertRaises(ValueError):
            EvaluationResult(score=90, verdict="pass")  # type: ignore[arg-type]

    def test_revision_contract_receives_only_structured_evaluation_context(self):
        evaluation = EvaluationResult(
            score=70,
            verdict=EvaluationVerdict.NEEDS_REVISION,
            issues=({"category": "causality"},),
        )
        revised = FakeReviser().revise(
            RevisionRequest(
                player_summary=self.retrieval_request.player_summary,
                deterministic_report=self.retrieval_request.deterministic_report,
                knowledge=KnowledgeEvidence.empty(),
                report="视野不足导致经济下降。",
                evaluation=evaluation,
            )
        )

        self.assertEqual("视野不足可能相关经济下降。", revised.report)


if __name__ == "__main__":
    unittest.main()
