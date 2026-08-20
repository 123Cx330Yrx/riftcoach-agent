from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.memory.models import OwnerId, RelationshipRole
from app.memory.typed_models import (
    MemoryTargetKind,
    MemoryTargetStatus,
    TypedMemoryRecordView,
)
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)


SessionFactory = Callable[[], Session]
_OWNER_ADAPTER = TypeAdapter(OwnerId)


class TypedMemoryQueryRepositoryError(RuntimeError):
    """Safe persistence error without SQL or private target body."""


class PostgresTypedMemoryQueryRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def list_preferences(
        self,
        *,
        owner_id: str,
        include_history: bool,
        limit: int,
    ) -> tuple[TypedMemoryRecordView, ...]:
        owner = _validate_owner(owner_id)
        bounded_limit = _validate_limit(limit)
        statement = sa.select(MemoryPreferenceRecord).where(
            MemoryPreferenceRecord.owner_id == owner,
            MemoryPreferenceRecord.hidden_at.is_(None),
        )
        if not include_history:
            statement = statement.where(MemoryPreferenceRecord.status == "active")
        statement = statement.order_by(
            MemoryPreferenceRecord.memory_key,
            MemoryPreferenceRecord.version.desc(),
        ).limit(bounded_limit)
        return self._load(statement, MemoryTargetKind.OWNER_PREFERENCE)

    def list_profile(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> tuple[TypedMemoryRecordView, ...] | None:
        return self._list_player_target(
            owner_id=owner_id,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
            target_kind=MemoryTargetKind.PLAYER_PROFILE,
        )

    def list_reviews(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> tuple[TypedMemoryRecordView, ...] | None:
        return self._list_player_target(
            owner_id=owner_id,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
            target_kind=MemoryTargetKind.REVIEW_MEMORY,
        )

    def _list_player_target(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
        target_kind: MemoryTargetKind,
    ) -> tuple[TypedMemoryRecordView, ...] | None:
        owner = _validate_owner(owner_id)
        if not isinstance(relationship_id, UUID):
            raise TypeError("relationship_id must be UUID")
        bounded_limit = _validate_limit(limit)
        record_type = (
            PlayerProfileRecord
            if target_kind is MemoryTargetKind.PLAYER_PROFILE
            else ReviewMemoryRecord
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    relationship = session.scalar(
                        sa.select(OwnerPlayerRelationshipRecord).where(
                            OwnerPlayerRelationshipRecord.owner_id == owner,
                            OwnerPlayerRelationshipRecord.relationship_id == relationship_id,
                            OwnerPlayerRelationshipRecord.status == "active",
                            OwnerPlayerRelationshipRecord.hidden_at.is_(None),
                        )
                    )
                    if relationship is None:
                        return None
                    if (
                        target_kind is MemoryTargetKind.PLAYER_PROFILE
                        and relationship.relationship_role != RelationshipRole.SELF.value
                    ):
                        return None
                    statement = sa.select(record_type).where(
                        record_type.owner_id == owner,
                        record_type.relationship_id == relationship_id,
                        record_type.player_subject_id == relationship.player_subject_id,
                        record_type.relationship_role == relationship.relationship_role,
                        record_type.hidden_at.is_(None),
                    )
                    if not include_history:
                        statement = statement.where(record_type.status == "active")
                    statement = statement.order_by(
                        record_type.memory_key,
                        record_type.version.desc(),
                    ).limit(bounded_limit)
                    records = tuple(session.scalars(statement))
                return tuple(_to_view(item, target_kind) for item in records)
        except SQLAlchemyError:
            raise TypedMemoryQueryRepositoryError("typed_memory_query_unavailable") from None
        except (TypeError, ValueError):
            raise TypedMemoryQueryRepositoryError("typed_memory_query_integrity_failed") from None

    def _load(self, statement, target_kind: MemoryTargetKind) -> tuple[TypedMemoryRecordView, ...]:
        try:
            with self._session_factory() as session:
                with session.begin():
                    records = tuple(session.scalars(statement))
                return tuple(_to_view(item, target_kind) for item in records)
        except SQLAlchemyError:
            raise TypedMemoryQueryRepositoryError("typed_memory_query_unavailable") from None
        except (TypeError, ValueError):
            raise TypedMemoryQueryRepositoryError("typed_memory_query_integrity_failed") from None


def _to_view(record, target_kind: MemoryTargetKind) -> TypedMemoryRecordView:
    player_scoped = target_kind is not MemoryTargetKind.OWNER_PREFERENCE
    return TypedMemoryRecordView(
        record_id=record.record_id,
        target_kind=target_kind,
        relationship_id=record.relationship_id if player_scoped else None,
        relationship_role=(
            RelationshipRole(record.relationship_role) if player_scoped else None
        ),
        memory_key=record.memory_key,
        version=record.version,
        status=MemoryTargetStatus(record.status),
        payload=record.payload,
        supersedes_record_id=record.supersedes_record_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _validate_owner(value: str) -> str:
    try:
        return _OWNER_ADAPTER.validate_python(value, strict=True)
    except ValueError:
        raise TypeError("owner_id is invalid") from None


def _validate_limit(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 100:
        raise TypeError("limit must be between 1 and 100")
    return value


__all__ = ["PostgresTypedMemoryQueryRepository", "TypedMemoryQueryRepositoryError"]
