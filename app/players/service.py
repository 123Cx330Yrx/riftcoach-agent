from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, TypeAlias
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

from app.players.fingerprint import compute_player_link_request_fingerprint
from app.players.models import (
    CreatePlayerLinkCommand,
    OwnerId,
    PendingPlayerLinkTask,
    PlayerLinkCapacityPolicy,
    PlayerLinkCreateDisposition,
    PlayerLinkCreateResult,
    PlayerLinkRepositoryCreateDisposition,
    PlayerLinkTaskView,
    PlayerProfilePage,
    PlayerProfileView,
    compute_alias_hash,
)
from app.players.ports import PlayerRepository


PlayerLinkServiceErrorCode: TypeAlias = Literal[
    "idempotency_conflict",
    "owner_capacity_exceeded",
    "global_capacity_exceeded",
    "link_not_found",
    "link_persistence_failed",
    "link_identity_invalid",
]
_PLAYER_LINK_SERVICE_ERROR_CODES = frozenset(
    {
        "idempotency_conflict",
        "owner_capacity_exceeded",
        "global_capacity_exceeded",
        "link_not_found",
        "link_persistence_failed",
        "link_identity_invalid",
    }
)
LinkTaskIdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]
_OWNER_ID_ADAPTER = TypeAdapter(OwnerId)


class PlayerLinkServiceError(RuntimeError):
    def __init__(self, code: PlayerLinkServiceErrorCode) -> None:
        if code not in _PLAYER_LINK_SERVICE_ERROR_CODES:
            raise ValueError("unsupported player link service error code")
        self.code = code
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str]:
        return {"code": self.code}


class PlayerLinkService:
    def __init__(
        self,
        *,
        repository: PlayerRepository,
        capacity: PlayerLinkCapacityPolicy | None = None,
        link_task_id_factory: LinkTaskIdFactory = uuid4,
        clock: Clock | None = None,
    ) -> None:
        for method_name in ("create_or_replay_link", "get_link_by_id"):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(link_task_id_factory):
            raise TypeError("link_task_id_factory must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")

        self._repository = repository
        self._capacity = capacity or PlayerLinkCapacityPolicy()
        self._link_task_id_factory = link_task_id_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, command: CreatePlayerLinkCommand) -> PlayerLinkCreateResult:
        if not isinstance(command, CreatePlayerLinkCommand):
            raise TypeError("command must be a CreatePlayerLinkCommand")

        try:
            pending = PendingPlayerLinkTask(
                link_task_id=self._link_task_id_factory(),
                owner_id=command.owner_id,
                idempotency_key=command.idempotency_key,
                request_fingerprint=compute_player_link_request_fingerprint(
                    task_kind="player_link",
                    schema_version="1.0",
                    routing_region=command.routing_region.value,
                    game_name=command.game_name,
                    tag_line=command.tag_line,
                    relationship_role=command.relationship_role.value,
                ),
                routing_region=command.routing_region,
                relationship_role=command.relationship_role,
                verification_status=command.derived_verification_status,
                game_name=command.game_name,
                tag_line=command.tag_line,
                alias_hash=compute_alias_hash(
                    game_name=command.game_name,
                    tag_line=command.tag_line,
                ),
                created_at=self._clock(),
            )
        except (StopIteration, TypeError, ValueError, ValidationError):
            raise PlayerLinkServiceError("link_identity_invalid") from None

        try:
            repository_result = self._repository.create_or_replay_link(
                pending,
                capacity=self._capacity,
            )
        except Exception:
            raise PlayerLinkServiceError("link_persistence_failed") from None

        if (
            repository_result.disposition
            is PlayerLinkRepositoryCreateDisposition.CREATED
        ):
            disposition = PlayerLinkCreateDisposition.CREATED
        elif (
            repository_result.disposition
            is PlayerLinkRepositoryCreateDisposition.REPLAYED
        ):
            disposition = PlayerLinkCreateDisposition.REPLAYED
        else:
            code_by_disposition: dict[
                PlayerLinkRepositoryCreateDisposition,
                PlayerLinkServiceErrorCode,
            ] = {
                PlayerLinkRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT: (
                    "idempotency_conflict"
                ),
                PlayerLinkRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED: (
                    "owner_capacity_exceeded"
                ),
                PlayerLinkRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED: (
                    "global_capacity_exceeded"
                ),
            }
            code = code_by_disposition.get(repository_result.disposition)
            if code is None:
                raise PlayerLinkServiceError("link_persistence_failed")
            raise PlayerLinkServiceError(code)

        assert repository_result.task is not None
        return PlayerLinkCreateResult(
            disposition=disposition,
            task=PlayerLinkTaskView.from_task(repository_result.task),
        )

    def get_link(self, *, owner_id: str, link_task_id: UUID) -> PlayerLinkTaskView:
        _validate_owner_scope(owner_id)
        if not isinstance(link_task_id, UUID):
            raise PlayerLinkServiceError("link_not_found")
        try:
            task = self._repository.get_link_by_id(
                owner_id=owner_id,
                link_task_id=link_task_id,
            )
        except Exception:
            raise PlayerLinkServiceError("link_persistence_failed") from None
        if task is None:
            raise PlayerLinkServiceError("link_not_found")
        return PlayerLinkTaskView.from_task(task)

    def list_profiles(
        self,
        *,
        owner_id: str,
        limit: int = 50,
    ) -> PlayerProfilePage:
        _validate_owner_scope(owner_id)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise PlayerLinkServiceError("link_identity_invalid")
        list_profiles = getattr(self._repository, "list_profiles", None)
        if not callable(list_profiles):
            raise PlayerLinkServiceError("link_persistence_failed")
        try:
            profiles = list_profiles(owner_id=owner_id, limit=limit)
        except Exception:
            raise PlayerLinkServiceError("link_persistence_failed") from None
        if (
            not isinstance(profiles, tuple)
            or len(profiles) > limit
            or any(not isinstance(profile, PlayerProfileView) for profile in profiles)
        ):
            raise PlayerLinkServiceError("link_persistence_failed")
        try:
            return PlayerProfilePage(items=profiles, limit=limit)
        except (TypeError, ValueError, ValidationError):
            raise PlayerLinkServiceError("link_persistence_failed") from None


def _validate_owner_scope(owner_id: str) -> None:
    try:
        _OWNER_ID_ADAPTER.validate_python(owner_id, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise PlayerLinkServiceError("link_not_found") from None


__all__ = [
    "PlayerLinkService",
    "PlayerLinkServiceError",
    "PlayerLinkServiceErrorCode",
]
