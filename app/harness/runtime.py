from __future__ import annotations

import json
from typing import Any, Mapping

from .models import ArtifactKind, HarnessConfig, RunManifest, RunStatus
from .state_machine import advance
from .steps import (
    CoachDraft,
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
from .store import FileRunStore


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
        """Run a bounded review workflow and publish only an accepted artifact."""

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

        try:
            knowledge = self.retriever.retrieve(
                RetrievalRequest(
                    player_summary=player_summary,
                    deterministic_report=deterministic_report,
                )
            )
            if not isinstance(knowledge, KnowledgeEvidence):
                raise TypeError("Retriever must return KnowledgeEvidence.")
        except Exception as exc:
            return self._finish_unsuccessful_run(
                deterministic_content,
                reason=self._step_failure_reason("retrieval", exc),
            )
        self.store.write_artifact(
            kind=ArtifactKind.RETRIEVAL_EVIDENCE,
            relative_path="knowledge/retrieval_evidence.json",
            content=self._knowledge_bytes(knowledge),
            schema_version="1.0",
            producer="retriever",
        )
        manifest = self._transition(RunStatus.KNOWLEDGE_READY)

        try:
            draft = self.generator.generate(
                GenerationRequest(
                    player_summary=player_summary,
                    deterministic_report=deterministic_report,
                    knowledge=knowledge,
                )
            )
            if not isinstance(draft, CoachDraft):
                raise TypeError("Generator must return CoachDraft.")
        except Exception as exc:
            return self._finish_unsuccessful_run(
                deterministic_content,
                reason=self._step_failure_reason("generation", exc),
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

        current_report = draft.report
        current_content = draft_content

        while True:
            try:
                evaluation = self.evaluator.evaluate(
                    EvaluationRequest(
                        player_summary=player_summary,
                        deterministic_report=deterministic_report,
                        knowledge=knowledge,
                        report=current_report,
                    )
                )
                self._validate_evaluation(evaluation)
            except Exception as exc:
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason=self._step_failure_reason("evaluation", exc),
                )

            manifest = self.store.read_manifest()
            attempt_id = manifest.attempt_id
            self.store.write_artifact(
                kind=ArtifactKind.EVALUATION_RESULT,
                relative_path=f"evaluations/evaluation_attempt_{attempt_id}.json",
                content=self._evaluation_bytes(evaluation),
                schema_version="1.0",
                producer="evaluator",
            )

            if self._passes_quality_gate(evaluation):
                self._transition(RunStatus.PASSED)
                return self._publish(current_content)

            if evaluation.verdict is not EvaluationVerdict.NEEDS_REVISION:
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason="evaluation_failed",
                )

            manifest = self.store.read_manifest()
            if manifest.revision_count >= self.config.max_revisions:
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason="revision_budget_exhausted",
                )

            self._transition(RunStatus.NEEDS_REVISION)
            manifest = self._transition(RunStatus.REVISING)

            try:
                revised = self.reviser.revise(
                    RevisionRequest(
                        player_summary=player_summary,
                        deterministic_report=deterministic_report,
                        knowledge=knowledge,
                        report=current_report,
                        evaluation=evaluation,
                    )
                )
                if not isinstance(revised, CoachDraft):
                    raise TypeError("Reviser must return CoachDraft.")
            except Exception as exc:
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason=self._step_failure_reason("revision", exc),
                )

            current_report = revised.report
            current_content = current_report.encode("utf-8")
            self.store.write_artifact(
                kind=ArtifactKind.REVISED_REPORT,
                relative_path=(
                    f"drafts/revised_report_attempt_{manifest.attempt_id}.md"
                ),
                content=current_content,
                schema_version="1.0",
                producer="reviser",
            )
            self._transition(RunStatus.RE_EVALUATING)

    def _transition(self, target: RunStatus) -> RunManifest:
        manifest = self.store.read_manifest()
        advance(manifest, target, attempt_id=manifest.attempt_id)
        self.store.write_manifest(manifest)
        return manifest

    def _passes_quality_gate(self, evaluation: EvaluationResult) -> bool:
        return (
            evaluation.verdict is EvaluationVerdict.PASS
            and evaluation.score >= self.config.publish_score_threshold
            and not evaluation.issues
        )

    @staticmethod
    def _validate_evaluation(evaluation: object) -> None:
        if not isinstance(evaluation, EvaluationResult):
            raise TypeError("Evaluator must return EvaluationResult.")
        if (
            evaluation.verdict is EvaluationVerdict.NEEDS_REVISION
            and not evaluation.issues
        ):
            raise ValueError("A revision verdict must include at least one issue.")
        if evaluation.verdict is EvaluationVerdict.PASS and evaluation.issues:
            raise ValueError("A passing evaluation must not include issues.")

    def _publish(self, content: bytes) -> RunManifest:
        self.store.write_artifact(
            kind=ArtifactKind.FINAL_REPORT,
            relative_path="output/final_report.md",
            content=content,
            schema_version="1.0",
            producer="review_harness.publisher",
        )
        return self._finish_terminal(
            RunStatus.PUBLISHED,
            decision="published",
            reason="quality_gate_passed",
        )

    def _finish_unsuccessful_run(
        self,
        deterministic_content: bytes,
        *,
        reason: str,
    ) -> RunManifest:
        if not self.config.allow_deterministic_fallback:
            return self._finish_terminal(
                RunStatus.REJECTED,
                decision="rejected",
                reason=reason,
            )

        self.store.write_artifact(
            kind=ArtifactKind.FINAL_REPORT,
            relative_path="output/final_report.md",
            content=deterministic_content,
            schema_version="1.0",
            producer="review_harness.deterministic_fallback",
        )
        return self._finish_terminal(
            RunStatus.DEGRADED,
            decision="deterministic_fallback",
            reason=reason,
        )

    def _finish_terminal(
        self,
        target: RunStatus,
        *,
        decision: str,
        reason: str,
    ) -> RunManifest:
        manifest = self.store.read_manifest()
        advance(
            manifest,
            target,
            attempt_id=manifest.attempt_id,
            reason=reason,
        )
        manifest.final_decision = decision
        self.store.write_manifest(manifest)
        return manifest

    @staticmethod
    def _step_failure_reason(step: str, error: Exception) -> str:
        return f"{step}_failed:{type(error).__name__}"

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
