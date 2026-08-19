from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerAliasRecord,
    PlayerLinkTaskRecord,
    PlayerSubjectRecord,
)
from app.players.models import (
    OwnerPlayerRelationshipRef,
    PendingPlayerLinkTask,
    PlayerLinkCapacityPolicy,
    PlayerLinkFailure,
    PlayerLinkRepositoryCreateDisposition,
    PlayerLinkRepositoryCreateResult,
    PlayerLinkStatus,
    PlayerLinkTask,
    RelationshipRole,
    ResolvedRiotAccount,
    RoutingRegion,
    VerificationStatus,
    WorkerId,
    compute_alias_hash,
)
from app.players.ports import PlayerRepositoryError


SessionFactory = Callable[[], Session]
_ACTIVE_STATUSES = (PlayerLinkStatus.QUEUED.value, PlayerLinkStatus.RUNNING.value)
_PLAYER_LINK_CREATE_ADVISORY_LOCK_ID = 593_231_842_002
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)
_RETRYABLE_FAILURE_CODES = frozenset(
    {"riot_rate_limited", "upstream_timeout", "upstream_unavailable"}
)


class PostgresPlayerRepository:
    """Short-transaction PostgreSQL persistence for player-link control state.

    The repository accepts an already resolved Riot account value.  It never
    owns a network client or callback, so Account-V1 cannot accidentally run
    while a database transaction or row lock is open.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def create_or_replay_link(
        self,
        pending: PendingPlayerLinkTask,
        *,
        capacity: PlayerLinkCapacityPolicy,
    ) -> PlayerLinkRepositoryCreateResult:
        if not isinstance(pending, PendingPlayerLinkTask):
            raise TypeError("pending must be a PendingPlayerLinkTask")
        if not isinstance(capacity, PlayerLinkCapacityPolicy):
            raise TypeError("capacity must be a PlayerLinkCapacityPolicy")

        try:
            with self._session_factory() as session:
                with session.begin():
                    session.execute(
                        sa.text(
                            "SELECT pg_advisory_xact_lock(:player_link_create_lock_id)"
                        ),
                        {
                            "player_link_create_lock_id": (
                                _PLAYER_LINK_CREATE_ADVISORY_LOCK_ID
                            )
                        },
                    )
                    result = self._create_or_replay_locked(
                        session,
                        pending=pending,
                        capacity=capacity,
                    )
                return result
        except PlayerRepositoryError:
            raise
        except SQLAlchemyError:
            raise PlayerRepositoryError("player_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise PlayerRepositoryError(
                "player_repository_integrity_failed"
            ) from None

    def get_link_by_id(
        self,
        *,
        owner_id: str,
        link_task_id: UUID,
    ) -> PlayerLinkTask | None:
        if not isinstance(owner_id, str) or not owner_id:
            raise TypeError("owner_id must be a non-empty string")
        if not isinstance(link_task_id, UUID):
            raise TypeError("link_task_id must be a UUID")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(PlayerLinkTaskRecord).where(
                            PlayerLinkTaskRecord.owner_id == owner_id,
                            PlayerLinkTaskRecord.link_task_id == link_task_id,
                        )
                    )
                    if record is None:
                        return None
                    task = self._map_record(session, record)
                return task
        except PlayerRepositoryError:
            raise
        except SQLAlchemyError:
            raise PlayerRepositoryError("player_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise PlayerRepositoryError(
                "player_repository_integrity_failed"
            ) from None

    def claim_next_link(
        self,
        *,
        worker_id: str,
        now: datetime,
    ) -> PlayerLinkTask | None:
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_now = _as_utc(now)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(PlayerLinkTaskRecord)
                        .where(
                            PlayerLinkTaskRecord.status
                            == PlayerLinkStatus.QUEUED.value
                        )
                        .order_by(
                            PlayerLinkTaskRecord.created_at.asc(),
                            PlayerLinkTaskRecord.link_task_id.asc(),
                        )
                        .limit(1)
                        .with_for_update(skip_locked=True)
                    )
                    if record is None:
                        return None
                    claim_time = max(
                        normalized_now,
                        _as_utc(record.created_at),
                        _as_utc(record.updated_at),
                    )
                    record.status = PlayerLinkStatus.RUNNING.value
                    record.worker_id = normalized_worker_id
                    record.claimed_at = claim_time
                    record.updated_at = claim_time
                    session.flush()
                    claimed = _record_to_link_task(record, relationship=None)
                return claimed
        except PlayerRepositoryError:
            raise
        except SQLAlchemyError:
            raise PlayerRepositoryError("player_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise PlayerRepositoryError(
                "player_repository_integrity_failed"
            ) from None

    def resolve_link(
        self,
        *,
        link_task_id: UUID,
        worker_id: str,
        resolved_account: ResolvedRiotAccount,
    ) -> PlayerLinkTask | None:
        if not isinstance(link_task_id, UUID):
            raise TypeError("link_task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        if not isinstance(resolved_account, ResolvedRiotAccount):
            raise TypeError("resolved_account must be a ResolvedRiotAccount")

        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(PlayerLinkTaskRecord)
                        .where(
                            PlayerLinkTaskRecord.link_task_id == link_task_id,
                            PlayerLinkTaskRecord.status
                            == PlayerLinkStatus.RUNNING.value,
                            PlayerLinkTaskRecord.worker_id == normalized_worker_id,
                        )
                        .with_for_update()
                    )
                    if record is None:
                        return None
                    if record.routing_region != resolved_account.routing_region.value:
                        raise PlayerRepositoryError(
                            "player_repository_integrity_failed"
                        )

                    terminal_time = _terminal_time(record)
                    subject_id = self._upsert_subject(
                        session,
                        resolved_account=resolved_account,
                        observed_at=terminal_time,
                    )
                    relationship = self._get_or_create_relationship(
                        session,
                        owner_id=record.owner_id,
                        subject_id=subject_id,
                        requested_role=RelationshipRole(record.relationship_role),
                        observed_at=terminal_time,
                    )

                    if relationship.relationship_role != record.relationship_role:
                        self._write_role_conflict(record, terminal_time=terminal_time)
                        session.flush()
                        terminal = _record_to_link_task(
                            record,
                            relationship=None,
                        )
                    else:
                        self._upsert_alias(
                            session,
                            subject_id=subject_id,
                            resolved_account=resolved_account,
                            observed_at=terminal_time,
                        )
                        record.status = PlayerLinkStatus.SUCCEEDED.value
                        record.updated_at = terminal_time
                        record.finished_at = terminal_time
                        record.terminal_reason = None
                        record.confirmed_game_name = resolved_account.game_name
                        record.confirmed_tag_line = resolved_account.tag_line
                        record.player_subject_id = subject_id
                        record.relationship_id = relationship.relationship_id
                        session.flush()
                        terminal = _record_to_link_task(
                            record,
                            relationship=relationship,
                        )
                return terminal
        except PlayerRepositoryError:
            raise
        except SQLAlchemyError:
            raise PlayerRepositoryError("player_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise PlayerRepositoryError(
                "player_repository_integrity_failed"
            ) from None

    def fail_link(
        self,
        *,
        link_task_id: UUID,
        worker_id: str,
        failure: PlayerLinkFailure,
    ) -> PlayerLinkTask | None:
        if not isinstance(link_task_id, UUID):
            raise TypeError("link_task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        if not isinstance(failure, PlayerLinkFailure):
            raise TypeError("failure must be a PlayerLinkFailure")

        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(PlayerLinkTaskRecord)
                        .where(
                            PlayerLinkTaskRecord.link_task_id == link_task_id,
                            PlayerLinkTaskRecord.status
                            == PlayerLinkStatus.RUNNING.value,
                            PlayerLinkTaskRecord.worker_id == normalized_worker_id,
                        )
                        .with_for_update()
                    )
                    if record is None:
                        return None
                    terminal_time = _terminal_time(record)
                    record.status = PlayerLinkStatus.FAILED.value
                    record.updated_at = terminal_time
                    record.finished_at = terminal_time
                    record.terminal_reason = failure.code
                    record.confirmed_game_name = None
                    record.confirmed_tag_line = None
                    record.player_subject_id = None
                    record.relationship_id = None
                    session.flush()
                    terminal = _record_to_link_task(record, relationship=None)
                return terminal
        except PlayerRepositoryError:
            raise
        except SQLAlchemyError:
            raise PlayerRepositoryError("player_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise PlayerRepositoryError(
                "player_repository_integrity_failed"
            ) from None

    def _create_or_replay_locked(
        self,
        session: Session,
        *,
        pending: PendingPlayerLinkTask,
        capacity: PlayerLinkCapacityPolicy,
    ) -> PlayerLinkRepositoryCreateResult:
        existing = session.scalar(
            sa.select(PlayerLinkTaskRecord).where(
                PlayerLinkTaskRecord.owner_id == pending.owner_id,
                PlayerLinkTaskRecord.idempotency_key == pending.idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint == pending.request_fingerprint:
                return PlayerLinkRepositoryCreateResult(
                    disposition=PlayerLinkRepositoryCreateDisposition.REPLAYED,
                    task=self._map_record(session, existing),
                )
            return PlayerLinkRepositoryCreateResult(
                disposition=(
                    PlayerLinkRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
                )
            )

        owner_active = session.scalar(
            sa.select(sa.func.count())
            .select_from(PlayerLinkTaskRecord)
            .where(
                PlayerLinkTaskRecord.owner_id == pending.owner_id,
                PlayerLinkTaskRecord.status.in_(_ACTIVE_STATUSES),
            )
        )
        if owner_active is None:
            raise PlayerRepositoryError("player_repository_integrity_failed")
        if owner_active >= capacity.owner_active_limit:
            return PlayerLinkRepositoryCreateResult(
                disposition=(
                    PlayerLinkRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED
                )
            )

        global_active = session.scalar(
            sa.select(sa.func.count())
            .select_from(PlayerLinkTaskRecord)
            .where(PlayerLinkTaskRecord.status.in_(_ACTIVE_STATUSES))
        )
        if global_active is None:
            raise PlayerRepositoryError("player_repository_integrity_failed")
        if global_active >= capacity.global_active_limit:
            return PlayerLinkRepositoryCreateResult(
                disposition=(
                    PlayerLinkRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED
                )
            )

        record = PlayerLinkTaskRecord(
            link_task_id=pending.link_task_id,
            task_kind=pending.task_kind,
            schema_version=pending.schema_version,
            owner_id=pending.owner_id,
            worker_id=None,
            idempotency_key=pending.idempotency_key,
            request_fingerprint=pending.request_fingerprint,
            game_name=pending.game_name,
            tag_line=pending.tag_line,
            routing_region=pending.routing_region.value,
            relationship_role=pending.relationship_role.value,
            alias_hash=pending.alias_hash,
            status=PlayerLinkStatus.QUEUED.value,
            created_at=pending.created_at,
            updated_at=pending.created_at,
            claimed_at=None,
            finished_at=None,
            terminal_reason=None,
            confirmed_game_name=None,
            confirmed_tag_line=None,
            player_subject_id=None,
            relationship_id=None,
        )
        session.add(record)
        session.flush()
        return PlayerLinkRepositoryCreateResult(
            disposition=PlayerLinkRepositoryCreateDisposition.CREATED,
            task=_record_to_link_task(record, relationship=None),
        )

    @staticmethod
    def _upsert_subject(
        session: Session,
        *,
        resolved_account: ResolvedRiotAccount,
        observed_at: datetime,
    ) -> UUID:
        statement = pg_insert(PlayerSubjectRecord).values(
            player_subject_id=uuid4(),
            game="lol",
            puuid=resolved_account.puuid,
            current_routing_region=resolved_account.routing_region.value,
            created_at=observed_at,
            updated_at=observed_at,
            last_resolved_at=observed_at,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_player_subjects_game_puuid",
            set_={
                "current_routing_region": resolved_account.routing_region.value,
                "updated_at": sa.func.greatest(
                    PlayerSubjectRecord.updated_at,
                    observed_at,
                ),
                "last_resolved_at": sa.func.greatest(
                    PlayerSubjectRecord.last_resolved_at,
                    observed_at,
                ),
            },
        ).returning(PlayerSubjectRecord.player_subject_id)
        subject_id = session.scalar(statement)
        if subject_id is None:
            raise PlayerRepositoryError("player_repository_integrity_failed")
        return subject_id

    @staticmethod
    def _get_or_create_relationship(
        session: Session,
        *,
        owner_id: str,
        subject_id: UUID,
        requested_role: RelationshipRole,
        observed_at: datetime,
    ) -> OwnerPlayerRelationshipRecord:
        relationship = session.scalar(
            sa.select(OwnerPlayerRelationshipRecord)
            .where(
                OwnerPlayerRelationshipRecord.owner_id == owner_id,
                OwnerPlayerRelationshipRecord.player_subject_id == subject_id,
            )
            .with_for_update()
        )
        if relationship is not None:
            return relationship

        verification = _verification_for_role(requested_role)
        relationship_id = uuid4()
        statement = (
            pg_insert(OwnerPlayerRelationshipRecord)
            .values(
                relationship_id=relationship_id,
                owner_id=owner_id,
                player_subject_id=subject_id,
                relationship_role=requested_role.value,
                verification_status=verification.value,
                status="active",
                created_at=observed_at,
                updated_at=observed_at,
                hidden_at=None,
            )
            .on_conflict_do_nothing(
                constraint=(
                    "uq_owner_player_relationships_owner_id_player_subject_id"
                )
            )
            .returning(OwnerPlayerRelationshipRecord.relationship_id)
        )
        inserted_id = session.scalar(statement)
        relationship = session.scalar(
            sa.select(OwnerPlayerRelationshipRecord)
            .where(
                OwnerPlayerRelationshipRecord.owner_id == owner_id,
                OwnerPlayerRelationshipRecord.player_subject_id == subject_id,
            )
            .with_for_update()
        )
        if relationship is None:
            raise PlayerRepositoryError("player_repository_integrity_failed")
        if inserted_id is not None and relationship.relationship_id != inserted_id:
            raise PlayerRepositoryError("player_repository_integrity_failed")
        return relationship

    @staticmethod
    def _upsert_alias(
        session: Session,
        *,
        subject_id: UUID,
        resolved_account: ResolvedRiotAccount,
        observed_at: datetime,
    ) -> None:
        alias_hash = compute_alias_hash(
            game_name=resolved_account.game_name,
            tag_line=resolved_account.tag_line,
        )
        statement = pg_insert(PlayerAliasRecord).values(
            player_alias_id=uuid4(),
            player_subject_id=subject_id,
            routing_region=resolved_account.routing_region.value,
            game_name=resolved_account.game_name,
            tag_line=resolved_account.tag_line,
            normalized_riot_id_hash=alias_hash,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_player_aliases_subject_region_riot_id_hash",
            set_={
                "game_name": resolved_account.game_name,
                "tag_line": resolved_account.tag_line,
                "last_seen_at": sa.func.greatest(
                    PlayerAliasRecord.last_seen_at,
                    observed_at,
                ),
            },
        )
        session.execute(statement)

    @staticmethod
    def _write_role_conflict(
        record: PlayerLinkTaskRecord,
        *,
        terminal_time: datetime,
    ) -> None:
        record.status = PlayerLinkStatus.FAILED.value
        record.updated_at = terminal_time
        record.finished_at = terminal_time
        record.terminal_reason = "relationship_role_conflict"
        record.confirmed_game_name = None
        record.confirmed_tag_line = None
        record.player_subject_id = None
        record.relationship_id = None

    @staticmethod
    def _map_record(
        session: Session,
        record: PlayerLinkTaskRecord,
    ) -> PlayerLinkTask:
        relationship = None
        if record.relationship_id is not None:
            relationship = session.scalar(
                sa.select(OwnerPlayerRelationshipRecord).where(
                    OwnerPlayerRelationshipRecord.relationship_id
                    == record.relationship_id,
                    OwnerPlayerRelationshipRecord.owner_id == record.owner_id,
                    OwnerPlayerRelationshipRecord.player_subject_id
                    == record.player_subject_id,
                    OwnerPlayerRelationshipRecord.relationship_role
                    == record.relationship_role,
                )
            )
            if relationship is None:
                raise PlayerRepositoryError("player_repository_integrity_failed")
        return _record_to_link_task(record, relationship=relationship)


def _record_to_link_task(
    record: PlayerLinkTaskRecord,
    *,
    relationship: OwnerPlayerRelationshipRecord | None,
) -> PlayerLinkTask:
    relationship_ref = None
    if relationship is not None:
        relationship_ref = OwnerPlayerRelationshipRef(
            relationship_id=relationship.relationship_id,
            player_subject_id=relationship.player_subject_id,
            relationship_role=RelationshipRole(relationship.relationship_role),
            verification_status=VerificationStatus(
                relationship.verification_status
            ),
        )
        verification_status = relationship_ref.verification_status
    else:
        verification_status = _verification_for_role(
            RelationshipRole(record.relationship_role)
        )

    failure = None
    if record.terminal_reason is not None:
        failure = PlayerLinkFailure(
            code=record.terminal_reason,
            retryable=record.terminal_reason in _RETRYABLE_FAILURE_CODES,
        )

    return PlayerLinkTask(
        link_task_id=record.link_task_id,
        task_kind=record.task_kind,
        schema_version=record.schema_version,
        owner_id=record.owner_id,
        idempotency_key=record.idempotency_key,
        request_fingerprint=record.request_fingerprint,
        routing_region=RoutingRegion(record.routing_region),
        relationship_role=RelationshipRole(record.relationship_role),
        verification_status=verification_status,
        game_name=record.game_name,
        tag_line=record.tag_line,
        alias_hash=record.alias_hash,
        status=PlayerLinkStatus(record.status),
        created_at=record.created_at,
        updated_at=record.updated_at,
        claimed_at=record.claimed_at,
        finished_at=record.finished_at,
        worker_id=record.worker_id,
        subject_id=record.player_subject_id,
        relationship=relationship_ref,
        confirmed_game_name=record.confirmed_game_name,
        confirmed_tag_line=record.confirmed_tag_line,
        failure=failure,
    )


def _verification_for_role(role: RelationshipRole) -> VerificationStatus:
    if role is RelationshipRole.SELF:
        return VerificationStatus.UNVERIFIED_CLAIM
    return VerificationStatus.NOT_APPLICABLE


def _validate_worker_id(value: str) -> str:
    try:
        return _WORKER_ID_ADAPTER.validate_python(value, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TypeError("worker_id must be a bounded safe identifier") from None


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _terminal_time(record: PlayerLinkTaskRecord) -> datetime:
    if record.claimed_at is None:
        raise PlayerRepositoryError("player_repository_integrity_failed")
    return max(
        datetime.now(timezone.utc),
        _as_utc(record.created_at),
        _as_utc(record.updated_at),
        _as_utc(record.claimed_at),
    )


__all__ = ["PostgresPlayerRepository"]
