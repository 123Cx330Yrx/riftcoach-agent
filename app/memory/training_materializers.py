"""Candidate-to-target materializers for Training Plan and Progress."""

from __future__ import annotations

from uuid import UUID

from app.memory.models import (
    CandidateKind,
    MaterializedMemoryReference,
    MemoryCandidate,
    ProvenanceKind,
)
from app.memory.ports import MaterializationSession
from app.memory.training_models import (
    parse_training_plan_write,
    parse_training_progress_write,
)
from app.memory.training_ports import TrainingTargetWriter


class TrainingMaterializerError(RuntimeError):
    """Safe contract failure; the outer Candidate transaction must roll back."""


class _TrainingMaterializer:
    candidate_kind: CandidateKind
    version: str
    writer_method: str

    def __init__(self, writer: TrainingTargetWriter) -> None:
        if not callable(getattr(writer, self.writer_method, None)):
            raise TypeError(f"writer must expose {self.writer_method}()")
        self._writer = writer

    def materialize(
        self,
        session: MaterializationSession,
        candidate: MemoryCandidate,
    ) -> MaterializedMemoryReference:
        if not isinstance(candidate, MemoryCandidate):
            raise TrainingMaterializerError("training_materializer_candidate_invalid")
        if candidate.candidate_kind is not self.candidate_kind:
            raise TrainingMaterializerError("training_materializer_kind_mismatch")
        parsed = self._parse(candidate)
        target_id = getattr(self._writer, self.writer_method)(
            session,
            candidate=candidate,
            parsed=parsed,
        )
        if not isinstance(target_id, UUID):
            raise TrainingMaterializerError("training_materializer_target_id_invalid")
        return MaterializedMemoryReference(
            target_kind=self.candidate_kind.value,
            target_id=target_id,
            materializer_version=self.version,
        )

    def _parse(self, candidate: MemoryCandidate):
        raise NotImplementedError


class TrainingPlanMaterializer(_TrainingMaterializer):
    candidate_kind = CandidateKind.TRAINING_PLAN
    version = "training-plan-v1"
    writer_method = "write_plan"

    def _parse(self, candidate: MemoryCandidate):
        if (
            candidate.provenance_kind is not ProvenanceKind.USER_STRUCTURED_INPUT
            or not candidate.requires_confirmation
            or candidate.memory_key != "active_plan"
        ):
            raise TrainingMaterializerError("training_plan_provenance_invalid")
        return parse_training_plan_write(
            target_scope=candidate.target_scope,
            candidate_kind=candidate.candidate_kind,
            operation=candidate.operation,
            relationship_role=candidate.relationship_role,
            proposal_payload=candidate.proposal_payload,
        )


class TrainingProgressMaterializer(_TrainingMaterializer):
    candidate_kind = CandidateKind.TRAINING_PROGRESS
    version = "training-progress-v1"
    writer_method = "write_progress"

    def _parse(self, candidate: MemoryCandidate):
        if (
            candidate.provenance_kind is not ProvenanceKind.DETERMINISTIC_RUN_FACT
            or candidate.source_task_id is None
            or candidate.source_run_id is None
            or candidate.source_artifact_sha256 is None
        ):
            raise TrainingMaterializerError("training_progress_provenance_invalid")
        parsed = parse_training_progress_write(
            target_scope=candidate.target_scope,
            candidate_kind=candidate.candidate_kind,
            operation=candidate.operation,
            relationship_role=candidate.relationship_role,
            proposal_payload=candidate.proposal_payload,
        )
        if candidate.memory_key != parsed.metric_key:
            raise TrainingMaterializerError("training_progress_metric_key_mismatch")
        return parsed


__all__ = [
    "TrainingMaterializerError",
    "TrainingPlanMaterializer",
    "TrainingProgressMaterializer",
]
