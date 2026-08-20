from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.memory.models import (
    CandidateCreateResult,
    CandidateMutationResult,
    CandidateKind,
    DecisionActorKind,
    CreateMemoryCandidateCommand,
    MaterializedMemoryReference,
    MemoryCandidate,
    MemoryCandidateView,
    MemoryConversationIdentity,
    PendingMemoryCandidate,
)


class MemoryCandidateRepositoryError(RuntimeError):
    """Persistence failure that must not cross the public boundary verbatim."""


class MaterializationSession(Protocol):
    """Restricted view of one Repository-owned SQLAlchemy transaction."""

    def add(self, instance: object) -> None: ...

    def flush(self) -> None: ...

    def execute(self, statement: object, params: object | None = None) -> Any: ...

    def scalar(self, statement: object) -> Any: ...


class MemoryCandidateMaterializer(Protocol):
    """A local, same-Session typed target writer.

    Implementations must only use the supplied transaction. They must not
    perform network/model/file I/O and must not commit or rollback the Session.
    """

    candidate_kind: CandidateKind
    version: str

    def materialize(
        self,
        session: MaterializationSession,
        candidate: MemoryCandidate,
    ) -> MaterializedMemoryReference: ...


MaterializerRegistry = Mapping[CandidateKind, MemoryCandidateMaterializer]


class MemoryCandidateRepository(Protocol):
    def get_conversation_identity(
        self,
        *,
        owner_id: str,
        conversation_id: UUID,
    ) -> MemoryConversationIdentity | None: ...

    def create_or_replay_candidate(
        self,
        pending: PendingMemoryCandidate,
        *,
        identity: MemoryConversationIdentity,
        requires_confirmation: bool,
        gate_policy_version: str,
    ) -> CandidateCreateResult: ...

    def get_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
    ) -> MemoryCandidate | None: ...

    def reject_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
        reason_code: str,
        now: datetime,
    ) -> CandidateMutationResult: ...

    def expire_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        now: datetime,
    ) -> CandidateMutationResult: ...

    def accept_candidate(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
        actor_kind: DecisionActorKind,
        now: datetime,
        materializers: MaterializerRegistry,
    ) -> CandidateMutationResult: ...


class MemoryCandidateServicePort(Protocol):
    def create(self, command: CreateMemoryCandidateCommand) -> MemoryCandidateView: ...

    def get(self, *, owner_id: str, candidate_id: UUID) -> MemoryCandidateView: ...

    def reject(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
    ) -> MemoryCandidateView: ...

    def accept(
        self,
        *,
        owner_id: str,
        candidate_id: UUID,
        actor_id: str,
    ) -> MemoryCandidateView: ...

__all__ = [
    "MaterializerRegistry",
    "MaterializationSession",
    "MemoryCandidateMaterializer",
    "MemoryCandidateRepository",
    "MemoryCandidateRepositoryError",
    "MemoryCandidateServicePort",
]
