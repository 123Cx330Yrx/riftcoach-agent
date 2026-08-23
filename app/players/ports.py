from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.players.models import (
    PendingPlayerLinkTask,
    PlayerLinkCapacityPolicy,
    PlayerLinkFailure,
    PlayerLinkRepositoryCreateResult,
    PlayerLinkTask,
    PlayerProfileView,
    ResolvedRiotAccount,
)


class PlayerRepositoryError(RuntimeError):
    """A repository failure that must be remapped before a public boundary."""


class PlayerRepository(Protocol):
    def create_or_replay_link(
        self,
        pending: PendingPlayerLinkTask,
        *,
        capacity: PlayerLinkCapacityPolicy,
    ) -> PlayerLinkRepositoryCreateResult: ...

    def get_link_by_id(
        self,
        *,
        owner_id: str,
        link_task_id: UUID,
    ) -> PlayerLinkTask | None: ...

    def list_profiles(
        self,
        *,
        owner_id: str,
        limit: int,
    ) -> tuple[PlayerProfileView, ...]: ...

    def claim_next_link(
        self,
        *,
        worker_id: str,
        now: datetime,
    ) -> PlayerLinkTask | None: ...

    def resolve_link(
        self,
        *,
        link_task_id: UUID,
        worker_id: str,
        resolved_account: ResolvedRiotAccount,
    ) -> PlayerLinkTask | None: ...

    def fail_link(
        self,
        *,
        link_task_id: UUID,
        worker_id: str,
        failure: PlayerLinkFailure,
    ) -> PlayerLinkTask | None: ...


__all__ = ["PlayerRepository", "PlayerRepositoryError"]
