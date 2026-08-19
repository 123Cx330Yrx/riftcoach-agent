from __future__ import annotations

from uuid import UUID

from app.players.models import CreatePlayerLinkCommand


class UnusedPlayerLinkService:
    """Explicit old-endpoint test dependency that rejects accidental use."""

    def create(self, command: CreatePlayerLinkCommand) -> object:
        del command
        raise AssertionError("player link service must not be called")

    def get_link(self, *, owner_id: str, link_task_id: UUID) -> object:
        del owner_id, link_task_id
        raise AssertionError("player link service must not be called")


__all__ = ["UnusedPlayerLinkService"]
