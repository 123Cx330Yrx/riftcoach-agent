from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.players.fingerprint import (
    canonical_player_link_request_bytes,
    compute_player_link_request_fingerprint,
)
from app.players.models import (
    CreatePlayerLinkCommand,
    OwnerPlayerRelationshipRef,
    PendingPlayerLinkTask,
    PlayerLinkCapacityPolicy,
    PlayerLinkCreateDisposition,
    PlayerLinkRepositoryCreateDisposition,
    PlayerLinkRepositoryCreateResult,
    PlayerLinkStatus,
    PlayerLinkTask,
    RelationshipRole,
    RoutingRegion,
    VerificationStatus,
)
from app.players.ports import PlayerRepository, PlayerRepositoryError
from app.players.service import PlayerLinkService, PlayerLinkServiceError


NOW = datetime(2026, 8, 19, 13, 0, 0, tzinfo=timezone.utc)
LINK_TASK_IDS = (
    UUID("30000000-0000-4000-8000-000000000001"),
    UUID("30000000-0000-4000-8000-000000000002"),
    UUID("30000000-0000-4000-8000-000000000003"),
)
SUBJECT_ID = UUID("30000000-0000-4000-8000-000000000010")
RELATIONSHIP_ID = UUID("30000000-0000-4000-8000-000000000011")


def command(
    *,
    owner_id: str = "owner-1",
    key: str = "link-1",
    riot_id: str = "DemoPlayer#KR1",
    routing_region: RoutingRegion = RoutingRegion.ASIA,
    relationship_role: RelationshipRole = RelationshipRole.SELF,
) -> CreatePlayerLinkCommand:
    return CreatePlayerLinkCommand(
        owner_id=owner_id,
        idempotency_key=key,
        riot_id=riot_id,
        routing_region=routing_region,
        relationship_role=relationship_role,
    )


def relationship_ref(
    *,
    role: RelationshipRole = RelationshipRole.SELF,
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED_CLAIM,
) -> OwnerPlayerRelationshipRef:
    return OwnerPlayerRelationshipRef(
        relationship_id=RELATIONSHIP_ID,
        player_subject_id=SUBJECT_ID,
        relationship_role=role,
        verification_status=verification_status,
    )


def task_from_pending(pending: PendingPlayerLinkTask) -> PlayerLinkTask:
    return PlayerLinkTask(
        link_task_id=pending.link_task_id,
        task_kind=pending.task_kind,
        schema_version=pending.schema_version,
        owner_id=pending.owner_id,
        idempotency_key=pending.idempotency_key,
        request_fingerprint=pending.request_fingerprint,
        routing_region=pending.routing_region,
        relationship_role=pending.relationship_role,
        verification_status=pending.verification_status,
        game_name=pending.game_name,
        tag_line=pending.tag_line,
        alias_hash=pending.alias_hash,
        status=PlayerLinkStatus.QUEUED,
        created_at=pending.created_at,
        updated_at=pending.created_at,
        claimed_at=None,
        finished_at=None,
        worker_id=None,
        subject_id=None,
        relationship=None,
        confirmed_game_name=None,
        confirmed_tag_line=None,
        failure=None,
    )


class FakePlayerRepository(PlayerRepository):
    def __init__(self) -> None:
        self.tasks: list[PlayerLinkTask] = []
        self.failure: Exception | None = None

    def create_or_replay_link(
        self,
        pending: PendingPlayerLinkTask,
        *,
        capacity: PlayerLinkCapacityPolicy,
    ) -> PlayerLinkRepositoryCreateResult:
        if self.failure is not None:
            raise self.failure
        existing = next(
            (
                task
                for task in self.tasks
                if task.owner_id == pending.owner_id
                and task.idempotency_key == pending.idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing.request_fingerprint == pending.request_fingerprint:
                return PlayerLinkRepositoryCreateResult(
                    disposition=PlayerLinkRepositoryCreateDisposition.REPLAYED,
                    task=existing,
                )
            return PlayerLinkRepositoryCreateResult(
                disposition=PlayerLinkRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
            )

        active = {PlayerLinkStatus.QUEUED, PlayerLinkStatus.RUNNING}
        owner_active = sum(
            task.owner_id == pending.owner_id and task.status in active
            for task in self.tasks
        )
        global_active = sum(task.status in active for task in self.tasks)
        if owner_active >= capacity.owner_active_limit:
            return PlayerLinkRepositoryCreateResult(
                disposition=PlayerLinkRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED
            )
        if global_active >= capacity.global_active_limit:
            return PlayerLinkRepositoryCreateResult(
                disposition=PlayerLinkRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED
            )

        created = task_from_pending(pending)
        self.tasks.append(created)
        return PlayerLinkRepositoryCreateResult(
            disposition=PlayerLinkRepositoryCreateDisposition.CREATED,
            task=created,
        )

    def get_link_by_id(
        self,
        *,
        owner_id: str,
        link_task_id: UUID,
    ) -> PlayerLinkTask | None:
        return next(
            (
                task
                for task in self.tasks
                if task.owner_id == owner_id and task.link_task_id == link_task_id
            ),
            None,
        )

    def claim_next_link(self, *, worker_id: str, now: datetime) -> PlayerLinkTask | None:
        raise NotImplementedError

    def resolve_link(self, **kwargs: object) -> PlayerLinkTask:
        raise NotImplementedError

    def fail_link(self, **kwargs: object) -> PlayerLinkTask:
        raise NotImplementedError


def service(
    repository: FakePlayerRepository,
    *,
    capacity: PlayerLinkCapacityPolicy | None = None,
    task_ids: tuple[UUID, ...] = LINK_TASK_IDS,
) -> PlayerLinkService:
    ids = iter(task_ids)
    return PlayerLinkService(
        repository=repository,
        capacity=capacity or PlayerLinkCapacityPolicy(),
        link_task_id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


def test_link_fingerprint_is_field_order_stable_and_semantically_sensitive() -> None:
    first = {
        "routing_region": "asia",
        "game_name": "DemoPlayer",
        "tag_line": "KR1",
        "relationship_role": "self",
    }
    reordered = {
        "relationship_role": "self",
        "tag_line": "KR1",
        "game_name": "DemoPlayer",
        "routing_region": "asia",
    }

    assert canonical_player_link_request_bytes(
        task_kind="player_link",
        schema_version="1.0",
        routing_region=first["routing_region"],
        game_name=first["game_name"],
        tag_line=first["tag_line"],
        relationship_role=first["relationship_role"],
    ) == canonical_player_link_request_bytes(
        task_kind="player_link",
        schema_version="1.0",
        routing_region=reordered["routing_region"],
        game_name=reordered["game_name"],
        tag_line=reordered["tag_line"],
        relationship_role=reordered["relationship_role"],
    )

    baseline = compute_player_link_request_fingerprint(
        task_kind="player_link",
        schema_version="1.0",
        routing_region="asia",
        game_name="DemoPlayer",
        tag_line="KR1",
        relationship_role="self",
    )
    assert len(baseline) == 64
    assert baseline != compute_player_link_request_fingerprint(
        task_kind="player_link",
        schema_version="1.0",
        routing_region="europe",
        game_name="DemoPlayer",
        tag_line="KR1",
        relationship_role="self",
    )
    assert baseline != compute_player_link_request_fingerprint(
        task_kind="player_link",
        schema_version="1.0",
        routing_region="asia",
        game_name="DemoPlayer",
        tag_line="KR2",
        relationship_role="self",
    )
    assert baseline != compute_player_link_request_fingerprint(
        task_kind="player_link",
        schema_version="1.0",
        routing_region="asia",
        game_name="OtherPlayer",
        tag_line="KR1",
        relationship_role="self",
    )
    assert baseline != compute_player_link_request_fingerprint(
        task_kind="player_link",
        schema_version="1.0",
        routing_region="asia",
        game_name="DemoPlayer",
        tag_line="KR1",
        relationship_role="observed",
    )
    with pytest.raises(ValueError, match="control"):
        compute_player_link_request_fingerprint(
            task_kind="player_link",
            schema_version="1.0",
            routing_region="asia",
            game_name="Demo\u0000Player",
            tag_line="KR1",
            relationship_role="self",
        )


def test_service_creates_and_replays_same_owner_key_and_fingerprint() -> None:
    repository = FakePlayerRepository()
    link_service = service(repository)

    created = link_service.create(command())
    replayed = link_service.create(command())

    assert created.disposition is PlayerLinkCreateDisposition.CREATED
    assert replayed.disposition is PlayerLinkCreateDisposition.REPLAYED
    assert replayed.task.link_task_id == created.task.link_task_id
    assert len(repository.tasks) == 1


def test_same_owner_key_with_different_fingerprint_is_safe_conflict() -> None:
    repository = FakePlayerRepository()
    link_service = service(repository)
    link_service.create(command())

    with pytest.raises(PlayerLinkServiceError) as exc_info:
        link_service.create(command(relationship_role=RelationshipRole.OBSERVED))

    assert exc_info.value.code == "idempotency_conflict"
    assert exc_info.value.to_public_dict() == {"code": "idempotency_conflict"}
    assert "DemoPlayer" not in repr(exc_info.value)
    assert len(repository.tasks) == 1


def test_owner_and_global_capacity_only_apply_to_new_active_links() -> None:
    owner_repository = FakePlayerRepository()
    owner_service = service(
        owner_repository,
        capacity=PlayerLinkCapacityPolicy(owner_active_limit=1, global_active_limit=3),
        task_ids=LINK_TASK_IDS + (UUID("30000000-0000-4000-8000-000000000004"),),
    )
    owner_service.create(command())
    assert owner_service.create(command()).disposition is PlayerLinkCreateDisposition.REPLAYED

    with pytest.raises(PlayerLinkServiceError) as owner_error:
        owner_service.create(command(key="link-2"))
    assert owner_error.value.code == "owner_capacity_exceeded"

    failed = owner_repository.tasks[0].model_copy(
        update={
            "status": PlayerLinkStatus.FAILED,
            "worker_id": "worker-1",
            "claimed_at": NOW,
            "finished_at": NOW,
            "failure": {"code": "player_not_found", "retryable": False},
        }
    )
    owner_repository.tasks[0] = PlayerLinkTask.model_validate(failed)
    replacement = owner_service.create(command(key="link-2"))
    assert replacement.task.link_task_id != LINK_TASK_IDS[0]

    global_repository = FakePlayerRepository()
    global_service = service(
        global_repository,
        capacity=PlayerLinkCapacityPolicy(owner_active_limit=2, global_active_limit=2),
    )
    global_service.create(command(owner_id="owner-1", key="one"))
    global_service.create(command(owner_id="owner-2", key="two"))
    with pytest.raises(PlayerLinkServiceError) as global_error:
        global_service.create(command(owner_id="owner-3", key="three"))
    assert global_error.value.code == "global_capacity_exceeded"


def test_server_generated_identity_or_time_failures_map_to_allowlisted_public_error() -> None:
    repository = FakePlayerRepository()

    invalid_id_service = PlayerLinkService(
        repository=repository,
        link_task_id_factory=lambda: "not-a-uuid",  # type: ignore[return-value]
        clock=lambda: NOW,
    )
    with pytest.raises(PlayerLinkServiceError) as id_error:
        invalid_id_service.create(command())
    assert id_error.value.code == "link_identity_invalid"

    invalid_clock_service = PlayerLinkService(
        repository=repository,
        link_task_id_factory=lambda: LINK_TASK_IDS[0],
        clock=lambda: NOW.replace(tzinfo=None),
    )
    with pytest.raises(PlayerLinkServiceError) as clock_error:
        invalid_clock_service.create(command())
    assert clock_error.value.code == "link_identity_invalid"


def test_repository_failures_are_hidden_behind_allowlisted_service_codes() -> None:
    repository = FakePlayerRepository()
    repository.failure = PlayerRepositoryError("secret-database-detail")
    link_service = service(repository)

    with pytest.raises(PlayerLinkServiceError) as exc_info:
        link_service.create(command())

    assert exc_info.value.code == "link_persistence_failed"
    assert str(exc_info.value) == "link_persistence_failed"
    assert "secret-database-detail" not in repr(exc_info.value)
