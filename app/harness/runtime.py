from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from .artifact_content import encode_json_artifact, encode_text_artifact
from .models import ArtifactKind, HarnessConfig, RunManifest, RunStatus
from .state_machine import advance
from .steps import (
    CoachDraft,
    DraftPreparationRequest,
    DraftPreparationResult,
    DraftPreparationStep,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    EvaluatorStep,
    KnowledgeEvidence,
    RevisionRequest,
    ReviserStep,
)
from .store import FileRunStore
from app.runtime.observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
    observe_runtime_signal,
)
from app.runtime.signals import (
    EvaluationCompletedSignal,
    HarnessTransitionedSignal,
    PublicationDecidedSignal,
    RuntimeEvaluationVerdict,
    RuntimeHarnessStatus,
    RuntimePublicationStatus,
)


class ReviewHarness:
    """Deterministic controller for one RiftCoach review run."""

    def __init__(
        self,
        *,
        store: FileRunStore,
        draft_preparer: DraftPreparationStep,
        evaluator: EvaluatorStep,
        reviser: ReviserStep,
        config: HarnessConfig | None = None,
        observer: RuntimeSignalObserver | None = None,
        draft_guard: Callable[[CoachDraft, KnowledgeEvidence], CoachDraft]
        | None = None,
    ) -> None:
        self.store = store
        self.draft_preparer = draft_preparer
        self.evaluator = evaluator
        self.reviser = reviser
        self.config = config or HarnessConfig()
        self.observer = observer
        if draft_guard is not None and not callable(draft_guard):
            raise TypeError("draft_guard must be callable or None")
        self.draft_guard = draft_guard

    def run(
        self,
        *,
        player_summary: Mapping[str, Any],
        deterministic_report: str,
        user_utterance: str | None = None,
    ) -> RunManifest:
        """Run a bounded review workflow and publish only an accepted artifact."""

        summary_content = encode_json_artifact(player_summary)
        deterministic_content = encode_text_artifact(deterministic_report)

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
            preparation = self.draft_preparer.prepare(
                DraftPreparationRequest(
                    player_summary=player_summary,
                    deterministic_report=deterministic_report,
                )
            )
            if not isinstance(preparation, DraftPreparationResult):
                raise TypeError(
                    "Draft preparer must return DraftPreparationResult."
                )
        except RuntimeObservationError:
            raise
        except Exception as exc:
            return self._finish_unsuccessful_run(
                deterministic_content,
                reason=self._step_failure_reason("draft_preparation", exc),
            )
        knowledge = preparation.knowledge
        draft = preparation.draft
        self.store.write_artifact(
            kind=ArtifactKind.RETRIEVAL_EVIDENCE,
            relative_path="knowledge/retrieval_evidence.json",
            content=self._knowledge_bytes(knowledge),
            schema_version="2.0",
            producer="draft_preparer",
        )
        manifest = self._transition(RunStatus.KNOWLEDGE_READY)

        if len(knowledge.source_ids) < self.config.minimum_evidence_sources:
            return self._finish_unsuccessful_run(
                deterministic_content,
                reason="evidence_required",
            )

        if self.draft_guard is not None:
            try:
                guarded = self.draft_guard(draft, knowledge)
                if not isinstance(guarded, CoachDraft):
                    raise TypeError("draft guard must return CoachDraft")
                draft = guarded
            except RuntimeObservationError:
                raise
            except Exception as exc:
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason=self._step_failure_reason("draft_safety", exc),
                )

        try:
            self._validate_report_citations(draft.report, knowledge)
        except Exception as exc:
            return self._finish_unsuccessful_run(
                deterministic_content,
                reason=self._step_failure_reason("draft_validation", exc),
            )
        draft_content = draft.report.encode("utf-8")
        self.store.write_artifact(
            kind=ArtifactKind.COACH_DRAFT,
            relative_path="drafts/coach_draft_attempt_0.md",
            content=draft_content,
            schema_version="1.0",
            producer="draft_preparer",
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
                        user_utterance=user_utterance,
                    )
                )
                self._validate_evaluation(evaluation)
            except RuntimeObservationError:
                raise
            except Exception as exc:
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason=self._step_failure_reason("evaluation", exc),
                )

            manifest = self.store.read_manifest()
            attempt_id = manifest.attempt_id
            evaluation_record = self.store.write_artifact(
                kind=ArtifactKind.EVALUATION_RESULT,
                relative_path=f"evaluations/evaluation_attempt_{attempt_id}.json",
                content=self._evaluation_bytes(evaluation),
                schema_version="1.0",
                producer="evaluator",
            )
            if self.observer is not None:
                self.store.read_artifact(evaluation_record)
                self._observe_evaluation(evaluation, attempt_id)

            if self._has_blocking_issue(evaluation):
                return self._finish_unsuccessful_run(
                    deterministic_content,
                    reason="security_policy_blocked",
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
                self._validate_report_citations(revised.report, knowledge)
            except RuntimeObservationError:
                raise
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
        before = self.store.read_manifest()
        before_status = before.status
        advance(before, target, attempt_id=before.attempt_id)
        self.store.write_manifest(before)
        if self.observer is None:
            return before
        persisted = self.store.read_manifest()
        self._observe_transition(
            before_status=before_status,
            persisted=persisted,
        )
        return persisted

    def _observe_transition(
        self,
        *,
        before_status: RunStatus,
        persisted: RunManifest,
    ) -> None:
        observe_runtime_signal(
            self.observer,
            HarnessTransitionedSignal(
                from_status=RuntimeHarnessStatus(before_status.value),
                to_status=RuntimeHarnessStatus(persisted.status.value),
                revision_count=persisted.revision_count,
            ),
        )

    def _observe_evaluation(
        self,
        evaluation: EvaluationResult,
        attempt_id: int,
    ) -> None:
        blocking_categories = tuple(
            sorted(
                {
                    "prompt_injection"
                    for issue in evaluation.issues
                    if isinstance(issue, Mapping)
                    and issue.get("category") == "prompt_injection"
                }
            )
        )
        observe_runtime_signal(
            self.observer,
            EvaluationCompletedSignal(
                attempt=attempt_id,
                score=evaluation.score,
                verdict=RuntimeEvaluationVerdict(evaluation.verdict.value),
                blocking_categories=blocking_categories,
            ),
        )

    def _passes_quality_gate(self, evaluation: EvaluationResult) -> bool:
        return (
            evaluation.verdict is EvaluationVerdict.PASS
            and evaluation.score >= self.config.publish_score_threshold
            and not evaluation.issues
        )

    @staticmethod
    def _has_blocking_issue(evaluation: EvaluationResult) -> bool:
        """Security issue categories are terminal policy decisions, not revisions."""

        return any(
            str(issue.get("category", "")) == "prompt_injection"
            for issue in evaluation.issues
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
        previous_status = manifest.status
        reason_code = self._reason_code(reason)
        advance(
            manifest,
            target,
            attempt_id=manifest.attempt_id,
            reason=reason_code,
        )
        manifest.final_decision = decision
        self.store.write_manifest(manifest)
        if self.observer is None:
            return manifest
        persisted = self.store.read_manifest()
        self._observe_transition(
            before_status=previous_status,
            persisted=persisted,
        )
        # Import lazily: app.runtime.models imports SkillExecutionRequest, while
        # the Harness package is also imported by the Skill package.
        from app.runtime.artifacts import project_artifact_references

        references = project_artifact_references(
            manifest=persisted,
            store=self.store,
        )
        final_report_digests = tuple(
            reference.sha256
            for reference in references
            if reference.kind == ArtifactKind.FINAL_REPORT.value
        )
        if target is RunStatus.REJECTED and final_report_digests:
            raise ValueError("rejected publication cannot reference a final report")
        if target is not RunStatus.REJECTED and len(final_report_digests) != 1:
            raise ValueError("terminal publication requires one final report")
        observe_runtime_signal(
            self.observer,
            PublicationDecidedSignal(
                publication_status=RuntimePublicationStatus(target.value),
                terminal_reason=reason_code,
                artifact_sha256s=()
                if target is RunStatus.REJECTED
                else final_report_digests,
            ),
        )
        return persisted

    @staticmethod
    def _step_failure_reason(step: str, error: Exception) -> str:
        return f"{step}_failed"

    @staticmethod
    def _reason_code(reason: str) -> str:
        return reason.split(":", maxsplit=1)[0]

    @staticmethod
    def _json_bytes(payload: Mapping[str, Any]) -> bytes:
        return encode_json_artifact(payload)

    @classmethod
    def _knowledge_bytes(cls, knowledge: KnowledgeEvidence) -> bytes:
        return cls._json_bytes(
            {
                "context": knowledge.context,
                "source_ids": list(knowledge.source_ids),
                "citations": [
                    {
                        "citation_id": citation.citation_id,
                        "chunk_id": citation.chunk_id,
                        "parent_id": citation.parent_id,
                        "source_id": citation.source_id,
                        "title": citation.title,
                        "content": citation.content,
                        "matched_content": citation.matched_content,
                        "version": citation.version,
                        "updated_at": citation.updated_at,
                    }
                    for citation in knowledge.citations
                ],
                "abstained": knowledge.abstained,
                "diagnostics": dict(knowledge.diagnostics),
            }
        )

    @staticmethod
    def _validate_report_citations(
        report: str,
        knowledge: KnowledgeEvidence,
    ) -> None:
        cited_ids = set(re.findall(r"\[(K\d+)\]", report))
        allowed_ids = {
            citation.citation_id
            for citation in knowledge.citations
        }
        unknown = sorted(cited_ids.difference(allowed_ids))
        if unknown:
            raise ValueError(
                "Coach report contains unknown knowledge citation IDs: "
                + ", ".join(unknown)
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
