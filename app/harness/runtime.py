from __future__ import annotations

import json
from typing import Any, Mapping

from .models import ArtifactKind, HarnessConfig, RunManifest, RunStatus
from .state_machine import advance
from .steps import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    EvaluatorStep,
    GenerationRequest,
    GeneratorStep,
    KnowledgeEvidence,
    RetrievalRequest,
    RetrieverStep,
    ReviserStep,
)
from .store import FileRunStore


class UnsupportedEvaluationOutcomeError(RuntimeError):
    """Raised for outcomes intentionally deferred to the Task 6 failure policy."""


class ReviewHarness:
    """Deterministic controller for one RiftCoach review run."""

    def __init__(
        self,
        *,
        store: FileRunStore,
        retriever: RetrieverStep,
        generator: GeneratorStep,
        evaluator: EvaluatorStep,
        reviser: ReviserStep,
        config: HarnessConfig | None = None,
    ) -> None:
        self.store = store
        self.retriever = retriever
        self.generator = generator
        self.evaluator = evaluator
        self.reviser = reviser
        self.config = config or HarnessConfig()

    def run(
        self,
        *,
        player_summary: Mapping[str, Any],
        deterministic_report: str,
    ) -> RunManifest:
        """Run the first-evaluation passing path and publish its verified draft."""

        summary_content = self._json_bytes(player_summary)
        deterministic_content = deterministic_report.encode("utf-8")

        manifest = RunManifest.new(self.store.run_id, self.config)
        self.store.create_run(manifest)

        self.store.write_artifact(
            kind=ArtifactKind.PLAYER_SUMMARY,
            relative_path="inputs/player_summary.json",
            content=summary_content,
            schema_version=str(player_summary.get("schema_version", "1.0")),
            producer="review_harness.input",
        )
        self.store.write_artifact(
            kind=ArtifactKind.DETERMINISTIC_REPORT,
            relative_path="inputs/deterministic_report.md",
            content=deterministic_content,
            schema_version="1.0",
            producer="review_harness.input",
        )
        manifest = self._transition(RunStatus.FACTS_READY)

        knowledge = self.retriever.retrieve(
            RetrievalRequest(
                player_summary=player_summary,
                deterministic_report=deterministic_report,
            )
        )
        self.store.write_artifact(
            kind=ArtifactKind.RETRIEVAL_EVIDENCE,
            relative_path="knowledge/retrieval_evidence.json",
            content=self._knowledge_bytes(knowledge),
            schema_version="1.0",
            producer="retriever",
        )
        manifest = self._transition(RunStatus.KNOWLEDGE_READY)

        draft = self.generator.generate(
            GenerationRequest(
                player_summary=player_summary,
                deterministic_report=deterministic_report,
                knowledge=knowledge,
            )
        )
        draft_content = draft.report.encode("utf-8")
        self.store.write_artifact(
            kind=ArtifactKind.COACH_DRAFT,
            relative_path="drafts/coach_draft_attempt_0.md",
            content=draft_content,
            schema_version="1.0",
            producer="generator",
        )
        manifest = self._transition(RunStatus.DRAFT_READY)
        manifest = self._transition(RunStatus.EVALUATING)

        evaluation = self.evaluator.evaluate(
            EvaluationRequest(
                player_summary=player_summary,
                deterministic_report=deterministic_report,
                knowledge=knowledge,
                report=draft.report,
            )
        )
        self.store.write_artifact(
            kind=ArtifactKind.EVALUATION_RESULT,
            relative_path="evaluations/evaluation_attempt_0.json",
            content=self._evaluation_bytes(evaluation),
            schema_version="1.0",
            producer="evaluator",
        )

        if not self._passes_quality_gate(evaluation):
            raise UnsupportedEvaluationOutcomeError(
                "Revision and failure outcomes are implemented in Harness Task 6."
            )

        manifest = self._transition(RunStatus.PASSED)
        self.store.write_artifact(
            kind=ArtifactKind.FINAL_REPORT,
            relative_path="output/final_report.md",
            content=draft_content,
            schema_version="1.0",
            producer="review_harness.publisher",
        )

        manifest = self.store.read_manifest()
        advance(manifest, RunStatus.PUBLISHED, attempt_id=manifest.attempt_id)
        manifest.final_decision = "published"
        self.store.write_manifest(manifest)
        return manifest

    def _transition(self, target: RunStatus) -> RunManifest:
        manifest = self.store.read_manifest()
        advance(manifest, target, attempt_id=manifest.attempt_id)
        self.store.write_manifest(manifest)
        return manifest

    def _passes_quality_gate(self, evaluation: EvaluationResult) -> bool:
        return (
            evaluation.verdict is EvaluationVerdict.PASS
            and evaluation.score >= self.config.publish_score_threshold
        )

    @staticmethod
    def _json_bytes(payload: Mapping[str, Any]) -> bytes:
        return (
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            + b"\n"
        )

    @classmethod
    def _knowledge_bytes(cls, knowledge: KnowledgeEvidence) -> bytes:
        return cls._json_bytes(
            {
                "context": knowledge.context,
                "source_ids": list(knowledge.source_ids),
            }
        )

    @classmethod
    def _evaluation_bytes(cls, evaluation: EvaluationResult) -> bytes:
        return cls._json_bytes(
            {
                "score": evaluation.score,
                "verdict": evaluation.verdict.value,
                "issues": list(evaluation.issues),
                "passed_checks": list(evaluation.passed_checks),
                "summary": evaluation.summary,
            }
        )
