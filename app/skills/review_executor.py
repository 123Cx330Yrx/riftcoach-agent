"""Compose reviewed Skill runs and rebuild typed outputs from persisted truth."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from pydantic import BaseModel, ValidationError

from app.agent.context import ContextBundle
from app.agent.draft import (
    AgentDraftPreparationError,
    AgentDraftPreparationResult,
    AgentFailureObservation,
)
from app.agent.loop import AgentRunResult
from app.harness.models import (
    ArtifactKind,
    HarnessConfig,
    RunManifest,
    RunStatus,
)
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    DraftPreparationRequest,
    DraftPreparationResult,
    EvaluationResult,
    EvaluationVerdict,
    EvaluatorStep,
    ReviserStep,
)
from app.harness.store import ArtifactIntegrityError, FileRunStore
from app.runtime.observer import (
    RuntimeObservationError,
    RuntimeSignalObserver,
)

from .execution import InputArtifactCommitment, ValidatedSkillExecution


_WARNING_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


class SkillReviewExecutionError(RuntimeError):
    """Raised when a reviewed Skill run cannot safely expose typed output."""


class _SkillAgentDraftPreparer(Protocol):
    def prepare(
        self,
        execution: ValidatedSkillExecution,
        context: ContextBundle,
    ) -> AgentDraftPreparationResult:
        """Prepare one unpublished Agent draft for a validated Skill."""


@dataclass(frozen=True)
class SkillReviewExecutionResult:
    """Typed terminal output plus its persisted Harness and Agent evidence."""

    output: BaseModel
    manifest: RunManifest
    agent_run: AgentRunResult | None
    agent_failure: AgentFailureObservation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.output, BaseModel):
            raise TypeError("output must be a Pydantic model")
        if not isinstance(self.manifest, RunManifest):
            raise TypeError("manifest must be a RunManifest")
        if not self.manifest.status.is_terminal:
            raise ValueError("manifest must be terminal")
        if self.agent_run is not None and not isinstance(
            self.agent_run,
            AgentRunResult,
        ):
            raise TypeError("agent_run must be an AgentRunResult or None")
        if self.agent_failure is not None and not isinstance(
            self.agent_failure,
            AgentFailureObservation,
        ):
            raise TypeError(
                "agent_failure must be an AgentFailureObservation or None"
            )
        if self.agent_run is not None and self.agent_failure is not None:
            raise ValueError("agent_run and agent_failure are mutually exclusive")


class _BoundAgentDraftPreparationStep:
    """Bind one validated Skill/context pair to the neutral Harness seam."""

    def __init__(
        self,
        *,
        draft_preparer: _SkillAgentDraftPreparer,
        execution: ValidatedSkillExecution,
        context: ContextBundle,
    ) -> None:
        self._draft_preparer = draft_preparer
        self._execution = execution
        self._context = context
        self.agent_run: AgentRunResult | None = None
        self.agent_failure: AgentFailureObservation | None = None

    def prepare(
        self,
        request: DraftPreparationRequest,
    ) -> DraftPreparationResult:
        typed_input = self._execution.typed_input
        if (
            dict(request.player_summary) != typed_input.player_summary
            or request.deterministic_report != typed_input.deterministic_report
        ):
            raise SkillReviewExecutionError(
                "Harness preparation input does not match validated Skill input"
            )
        try:
            result = self._draft_preparer.prepare(
                self._execution,
                self._context,
            )
        except AgentDraftPreparationError as exc:
            self.agent_failure = exc.failure
            raise SkillReviewExecutionError(
                "agent draft preparation failed"
            ) from exc
        except RuntimeObservationError:
            raise
        except Exception as exc:
            raise SkillReviewExecutionError(
                "agent draft preparer raised an unexpected error"
            ) from exc
        if not isinstance(result, AgentDraftPreparationResult):
            raise SkillReviewExecutionError(
                "agent draft preparer returned an invalid contract"
            )
        self.agent_run = result.agent_run
        return DraftPreparationResult(
            draft=result.draft,
            knowledge=result.knowledge,
        )


class SkillReviewExecutor:
    """Run one validated Skill Agent under the existing ReviewHarness."""

    def __init__(
        self,
        *,
        runs_root: str | Path,
        draft_preparer: _SkillAgentDraftPreparer,
        evaluator: EvaluatorStep,
        reviser: ReviserStep,
        output_builder: SkillTerminalOutputBuilder | None = None,
        max_revisions: int | None = None,
        allow_deterministic_fallback: bool | None = None,
        minimum_evidence_sources: int | None = None,
        draft_guard: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        if not callable(getattr(draft_preparer, "prepare", None)):
            raise TypeError("draft_preparer must provide prepare()")
        if not callable(getattr(evaluator, "evaluate", None)):
            raise TypeError("evaluator must provide evaluate()")
        if not callable(getattr(reviser, "revise", None)):
            raise TypeError("reviser must provide revise()")
        self._runs_root = Path(runs_root).resolve()
        self._draft_preparer = draft_preparer
        self._evaluator = evaluator
        self._reviser = reviser
        self._output_builder = output_builder or SkillTerminalOutputBuilder()
        if max_revisions is not None and (
            isinstance(max_revisions, bool)
            or not isinstance(max_revisions, int)
            or max_revisions < 0
        ):
            raise ValueError("max_revisions must be a non-negative integer")
        self._max_revisions = max_revisions
        if allow_deterministic_fallback is not None and not isinstance(
            allow_deterministic_fallback,
            bool,
        ):
            raise TypeError("allow_deterministic_fallback must be a bool or None")
        self._allow_deterministic_fallback = allow_deterministic_fallback
        if minimum_evidence_sources is not None and (
            isinstance(minimum_evidence_sources, bool)
            or not isinstance(minimum_evidence_sources, int)
            or minimum_evidence_sources < 0
        ):
            raise ValueError(
                "minimum_evidence_sources must be a non-negative integer or None"
            )
        self._minimum_evidence_sources = minimum_evidence_sources
        if draft_guard is not None and not callable(draft_guard):
            raise TypeError("draft_guard must be callable or None")
        self._draft_guard = draft_guard

    def execute(
        self,
        *,
        execution: ValidatedSkillExecution,
        context: ContextBundle,
        observer: RuntimeSignalObserver | None = None,
    ) -> SkillReviewExecutionResult:
        self._validate_execution_context(execution, context)
        quality_gate = execution.skill.manifest.quality_gate
        if not quality_gate.required:
            raise SkillReviewExecutionError(
                "SkillReviewExecutor requires a mandatory quality gate"
            )

        store = FileRunStore(self._runs_root, execution.run_id)
        bound_preparer = _BoundAgentDraftPreparationStep(
            draft_preparer=self._draft_preparer,
            execution=execution,
            context=context,
        )
        config = HarnessConfig(
            publish_score_threshold=quality_gate.minimum_score,
            max_revisions=(
                HarnessConfig().max_revisions
                if self._max_revisions is None
                else self._max_revisions
            ),
            allow_deterministic_fallback=(
                quality_gate.allow_deterministic_fallback
                if self._allow_deterministic_fallback is None
                else self._allow_deterministic_fallback
            ),
            minimum_evidence_sources=(
                0
                if self._minimum_evidence_sources is None
                else self._minimum_evidence_sources
            ),
        )
        typed_input = execution.typed_input
        try:
            ReviewHarness(
                store=store,
                draft_preparer=bound_preparer,
                evaluator=self._evaluator,
                reviser=self._reviser,
                config=config,
                observer=observer,
                draft_guard=self._draft_guard,
            ).run(
                player_summary=typed_input.player_summary,
                deterministic_report=typed_input.deterministic_report,
                user_utterance=execution.user_utterance,
            )
        except RuntimeObservationError:
            raise
        except Exception as exc:
            raise SkillReviewExecutionError(
                "review Harness execution failed"
            ) from exc

        output = self._output_builder.build(
            execution=execution,
            store=store,
        )
        manifest = store.read_manifest()
        return SkillReviewExecutionResult(
            output=output,
            manifest=manifest,
            agent_run=bound_preparer.agent_run,
            agent_failure=bound_preparer.agent_failure,
        )

    @staticmethod
    def _validate_execution_context(
        execution: ValidatedSkillExecution,
        context: ContextBundle,
    ) -> None:
        if not isinstance(execution, ValidatedSkillExecution):
            raise SkillReviewExecutionError(
                "Skill review requires a validated execution"
            )
        if not isinstance(context, ContextBundle):
            raise SkillReviewExecutionError(
                "Skill review requires a ContextBundle"
            )
        identity = (
            context.run_id,
            context.skill_name,
            context.skill_version,
        )
        expected = (
            execution.run_id,
            execution.skill.manifest.name,
            execution.skill.manifest.version,
        )
        if identity != expected:
            raise SkillReviewExecutionError(
                "execution and context identity mismatch"
            )


class SkillTerminalOutputBuilder:
    """Project a terminal Harness run into its declared Skill Output model."""

    def build(
        self,
        *,
        execution: ValidatedSkillExecution,
        store: FileRunStore,
    ) -> BaseModel:
        if not isinstance(execution, ValidatedSkillExecution):
            raise SkillReviewExecutionError(
                "terminal output requires a validated Skill execution"
            )
        if not isinstance(store, FileRunStore):
            raise SkillReviewExecutionError(
                "terminal output requires a FileRunStore"
            )
        if store.run_id != execution.run_id:
            raise SkillReviewExecutionError(
                "terminal run identity does not match Skill execution"
            )

        try:
            manifest = store.read_manifest()
        except Exception as exc:
            raise SkillReviewExecutionError(
                "terminal manifest validation failed"
            ) from exc
        self._validate_terminal_manifest(manifest, execution)
        self._validate_input_commitments(manifest, execution, store)

        try:
            report = self._read_final_report(manifest, store)
            score = self._read_final_evaluation_score(manifest, store)
            source_ids = self._read_evidence_source_ids(manifest, store)
        except (ArtifactIntegrityError, KeyError, TypeError, ValueError) as exc:
            raise SkillReviewExecutionError(
                "terminal artifact validation failed"
            ) from exc

        payload: dict[str, Any] = {
            "run_id": manifest.run_id,
            "status": manifest.status.value,
            "report": report,
            "evaluation_score": score,
            "evidence_source_ids": source_ids,
            "warnings": self._terminal_warnings(manifest),
        }
        typed_input = execution.typed_input
        if "target_match_id" in execution.skill.output_model.model_fields:
            target_match_id = getattr(typed_input, "target_match_id", None)
            if not isinstance(target_match_id, str) or not target_match_id.strip():
                raise SkillReviewExecutionError(
                    "single-match terminal identity is missing"
                )
            payload["target_match_id"] = target_match_id

        try:
            return execution.skill.output_model.model_validate(payload)
        except ValidationError as exc:
            raise SkillReviewExecutionError(
                "declared Skill output validation failed"
            ) from exc

    @staticmethod
    def _validate_terminal_manifest(
        manifest: RunManifest,
        execution: ValidatedSkillExecution,
    ) -> None:
        if manifest.run_id != execution.run_id:
            raise SkillReviewExecutionError(
                "terminal manifest run identity mismatch"
            )
        if not manifest.status.is_terminal:
            raise SkillReviewExecutionError(
                "Skill output requires a terminal Harness manifest"
            )
        expected_decision = {
            RunStatus.PUBLISHED: "published",
            RunStatus.DEGRADED: "deterministic_fallback",
            RunStatus.REJECTED: "rejected",
        }[manifest.status]
        if manifest.final_decision != expected_decision:
            raise SkillReviewExecutionError(
                "terminal manifest decision is inconsistent"
            )

    @classmethod
    def _validate_input_commitments(
        cls,
        manifest: RunManifest,
        execution: ValidatedSkillExecution,
        store: FileRunStore,
    ) -> None:
        cls._validate_input_commitment(
            manifest,
            store,
            execution.input_artifacts.player_summary,
        )
        cls._validate_input_commitment(
            manifest,
            store,
            execution.input_artifacts.deterministic_report,
        )

    @classmethod
    def _validate_input_commitment(
        cls,
        manifest: RunManifest,
        store: FileRunStore,
        commitment: InputArtifactCommitment,
    ) -> None:
        record = cls._require_single_record(manifest, commitment.kind)
        if (
            record.get("run_id") != manifest.run_id
            or record.get("schema_version") != commitment.schema_version
            or record.get("sha256") != commitment.sha256
        ):
            raise SkillReviewExecutionError(
                f"input artifact commitment mismatch: {commitment.kind.value}"
            )
        try:
            store.read_artifact(record)
        except (ArtifactIntegrityError, KeyError, OSError, ValueError) as exc:
            raise SkillReviewExecutionError(
                f"input artifact commitment unreadable: {commitment.kind.value}"
            ) from exc

    @classmethod
    def _read_final_report(
        cls,
        manifest: RunManifest,
        store: FileRunStore,
    ) -> str | None:
        records = cls._records(manifest, ArtifactKind.FINAL_REPORT)
        if manifest.status is RunStatus.REJECTED:
            if records:
                raise ValueError("rejected run cannot contain a final report")
            return None
        if len(records) != 1:
            raise ValueError("published/degraded run requires one final report")
        record = records[0]
        if record.get("schema_version") != "1.0":
            raise ValueError("unexpected final report schema")
        report = store.read_artifact(record).decode("utf-8")
        if not report.strip():
            raise ValueError("final report must not be blank")
        return report

    @classmethod
    def _read_final_evaluation_score(
        cls,
        manifest: RunManifest,
        store: FileRunStore,
    ) -> int | None:
        records = cls._records(manifest, ArtifactKind.EVALUATION_RESULT)
        if not records:
            return None
        expected_path = (
            f"evaluations/evaluation_attempt_{manifest.attempt_id}.json"
        )
        matching = [
            record
            for record in records
            if record.get("path") == expected_path
        ]
        if len(matching) != 1:
            raise ValueError("final evaluation artifact is missing or ambiguous")
        record = matching[0]
        if record.get("schema_version") != "1.0":
            raise ValueError("unexpected evaluation schema")
        payload = json.loads(store.read_artifact(record).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("evaluation artifact must contain an object")
        evaluation = EvaluationResult(
            score=payload["score"],
            verdict=EvaluationVerdict(payload["verdict"]),
            issues=tuple(payload.get("issues", ())),
            passed_checks=tuple(payload.get("passed_checks", ())),
            summary=payload.get("summary", ""),
        )
        return evaluation.score

    @classmethod
    def _read_evidence_source_ids(
        cls,
        manifest: RunManifest,
        store: FileRunStore,
    ) -> tuple[str, ...]:
        records = cls._records(manifest, ArtifactKind.RETRIEVAL_EVIDENCE)
        if not records:
            return ()
        if len(records) != 1:
            raise ValueError("retrieval evidence artifact is ambiguous")
        record = records[0]
        if record.get("schema_version") != "2.0":
            raise ValueError("unexpected retrieval evidence schema")
        payload = json.loads(store.read_artifact(record).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("retrieval evidence must contain an object")
        raw_source_ids = payload.get("source_ids")
        if not isinstance(raw_source_ids, list):
            raise ValueError("retrieval evidence source_ids must be a list")
        source_ids = tuple(raw_source_ids)
        if any(
            not isinstance(value, str) or not value.strip()
            for value in source_ids
        ):
            raise ValueError("retrieval evidence source IDs must be non-blank strings")
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("retrieval evidence source IDs must be unique")
        return source_ids

    @staticmethod
    def _terminal_warnings(manifest: RunManifest) -> tuple[str, ...]:
        if manifest.status is RunStatus.PUBLISHED:
            return ()
        if not manifest.transitions:
            raise SkillReviewExecutionError(
                "terminal manifest has no transition history"
            )
        terminal = manifest.transitions[-1]
        if terminal.get("to") != manifest.status.value:
            raise SkillReviewExecutionError(
                "terminal transition does not match manifest status"
            )
        reason = terminal.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise SkillReviewExecutionError(
                "unsuccessful terminal transition requires a reason"
            )
        reason_code = reason.split(":", maxsplit=1)[0]
        if not _WARNING_CODE.fullmatch(reason_code):
            raise SkillReviewExecutionError(
                "terminal reason is not a safe warning code"
            )
        prefix = (
            "deterministic_fallback"
            if manifest.status is RunStatus.DEGRADED
            else "report_rejected"
        )
        return tuple(dict.fromkeys((prefix, reason_code)))

    @classmethod
    def _require_single_record(
        cls,
        manifest: RunManifest,
        kind: ArtifactKind,
    ) -> dict[str, Any]:
        records = cls._records(manifest, kind)
        if len(records) != 1:
            raise SkillReviewExecutionError(
                f"terminal run requires one {kind.value} artifact"
            )
        return records[0]

    @staticmethod
    def _records(
        manifest: RunManifest,
        kind: ArtifactKind,
    ) -> list[dict[str, Any]]:
        return [
            record
            for record in manifest.artifacts
            if record.get("kind") == kind.value
        ]


__all__ = [
    "SkillReviewExecutionError",
    "SkillReviewExecutionResult",
    "SkillReviewExecutor",
    "SkillTerminalOutputBuilder",
]
