"""Candidate-to-target materializers for the 6B-6 typed memory families."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.memory.models import CandidateKind, MaterializedMemoryReference, MemoryCandidate
from app.memory.ports import MaterializationSession
from app.memory.typed_models import ParsedTypedMemoryWrite, parse_typed_memory_write


class TypedMemoryMaterializerError(RuntimeError):
    """Safe materializer contract failure; target transaction must roll back."""


class TypedMemoryTargetWriter(Protocol):
    """Writes one parsed target using the Repository-owned transaction."""

    def write(
        self,
        session: MaterializationSession,
        *,
        candidate: MemoryCandidate,
        parsed: ParsedTypedMemoryWrite,
    ) -> UUID: ...


class _TypedMemoryMaterializer:
    candidate_kind: CandidateKind
    version: str

    def __init__(self, writer: TypedMemoryTargetWriter) -> None:
        if not callable(getattr(writer, "write", None)):
            raise TypeError("writer must expose write()")
        self._writer = writer

    def materialize(
        self,
        session: MaterializationSession,
        candidate: MemoryCandidate,
    ) -> MaterializedMemoryReference:
        if not isinstance(candidate, MemoryCandidate):
            raise TypedMemoryMaterializerError("typed_materializer_candidate_invalid")
        if candidate.candidate_kind is not self.candidate_kind:
            raise TypedMemoryMaterializerError("typed_materializer_kind_mismatch")
        parsed = parse_typed_memory_write(
            target_scope=candidate.target_scope,
            candidate_kind=candidate.candidate_kind,
            memory_key=candidate.memory_key,
            operation=candidate.operation,
            relationship_role=candidate.relationship_role,
            proposal_payload=candidate.proposal_payload,
        )
        target_id = self._writer.write(
            session,
            candidate=candidate,
            parsed=parsed,
        )
        if not isinstance(target_id, UUID):
            raise TypedMemoryMaterializerError("typed_materializer_target_id_invalid")
        return MaterializedMemoryReference(
            target_kind=self.candidate_kind.value,
            target_id=target_id,
            materializer_version=self.version,
        )


class OwnerPreferenceMaterializer(_TypedMemoryMaterializer):
    candidate_kind = CandidateKind.OWNER_PREFERENCE
    version = "owner-preference-v1"


class PlayerProfileMaterializer(_TypedMemoryMaterializer):
    candidate_kind = CandidateKind.PLAYER_PROFILE
    version = "player-profile-v1"


class ReviewMemoryMaterializer(_TypedMemoryMaterializer):
    candidate_kind = CandidateKind.REVIEW_MEMORY
    version = "review-memory-v1"


__all__ = [
    "OwnerPreferenceMaterializer",
    "PlayerProfileMaterializer",
    "ReviewMemoryMaterializer",
    "TypedMemoryMaterializerError",
    "TypedMemoryTargetWriter",
]
