from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.memory.context_models import (
    MemoryContextBinding,
    MemoryContextRecord,
    MemoryContextRecordKind,
    MemoryContextSnapshot,
)
from app.persistence.conversation_records import ConversationMessageRecord, ConversationRecord
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord
from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)
from app.players.models import RelationshipRole


SessionFactory = Callable[[], Session]
_MESSAGE_LIMIT = 12
_PREFERENCE_LIMIT = 16
_PROFILE_LIMIT = 16
_REVIEW_LIMIT = 12
_PROGRESS_LIMIT = 12


class MemoryContextRepositoryError(RuntimeError):
    """Body-free selector failure."""


class PostgresMemoryContextRepository:
    """Load one bounded legal snapshot in a single read-only transaction."""

    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def load(self, binding: MemoryContextBinding) -> MemoryContextSnapshot:
        if not isinstance(binding, MemoryContextBinding):
            raise TypeError("binding must be a MemoryContextBinding")
        try:
            with self._session_factory() as session:
                with session.begin():
                    if not _binding_exists(session, binding):
                        raise MemoryContextRepositoryError(
                            "memory_context_unavailable"
                        )
                    records = [
                        *_preference_records(session, binding),
                        *_plan_records(session, binding),
                        *_profile_records(session, binding),
                        *_progress_records(session, binding),
                        *_review_records(session, binding),
                        *_message_records(session, binding),
                    ]
            records.sort(key=lambda row: (-row.priority, row.stable_order))
            return MemoryContextSnapshot(binding=binding, records=tuple(records))
        except MemoryContextRepositoryError:
            raise
        except SQLAlchemyError:
            raise MemoryContextRepositoryError(
                "memory_context_repository_unavailable"
            ) from None
        except (TypeError, ValueError):
            raise MemoryContextRepositoryError(
                "memory_context_integrity_failed"
            ) from None


def _binding_exists(session: Session, binding: MemoryContextBinding) -> bool:
    relationship = session.scalar(
        sa.select(OwnerPlayerRelationshipRecord.relationship_id).where(
            OwnerPlayerRelationshipRecord.owner_id == binding.owner_id,
            OwnerPlayerRelationshipRecord.relationship_id
            == binding.relationship_id,
            OwnerPlayerRelationshipRecord.player_subject_id
            == binding.player_subject_id,
            OwnerPlayerRelationshipRecord.relationship_role
            == binding.relationship_role.value,
            OwnerPlayerRelationshipRecord.status == "active",
            OwnerPlayerRelationshipRecord.hidden_at.is_(None),
        )
    )
    if relationship is None:
        return False
    conversation = session.scalar(
        sa.select(ConversationRecord.conversation_id).where(
            ConversationRecord.owner_id == binding.owner_id,
            ConversationRecord.conversation_id == binding.conversation_id,
            ConversationRecord.relationship_id == binding.relationship_id,
            ConversationRecord.player_subject_id == binding.player_subject_id,
            ConversationRecord.relationship_role
            == binding.relationship_role.value,
            ConversationRecord.status != "hidden",
        )
    )
    return conversation is not None


def _message_records(
    session: Session,
    binding: MemoryContextBinding,
) -> tuple[MemoryContextRecord, ...]:
    rows = list(
        session.scalars(
            sa.select(ConversationMessageRecord)
            .where(
                ConversationMessageRecord.owner_id == binding.owner_id,
                ConversationMessageRecord.conversation_id
                == binding.conversation_id,
                ConversationMessageRecord.relationship_id
                == binding.relationship_id,
                ConversationMessageRecord.player_subject_id
                == binding.player_subject_id,
                ConversationMessageRecord.relationship_role
                == binding.relationship_role.value,
                ConversationMessageRecord.hidden_at.is_(None),
            )
            .order_by(ConversationMessageRecord.sequence_no.desc())
            .limit(_MESSAGE_LIMIT)
        )
    )
    rows.reverse()
    return tuple(
        MemoryContextRecord(
            kind=MemoryContextRecordKind.MESSAGE,
            record_id=row.message_id,
            version=row.sequence_no,
            content_sha256=row.content_sha256,
            content=_canonical_json(
                {
                    "role": row.role,
                    "content": row.content,
                    "sequence_no": row.sequence_no,
                }
            ),
            priority=300,
            stable_order=f"message:{row.sequence_no:010d}",
            relationship_role=RelationshipRole(row.relationship_role),
        )
        for row in rows
    )


def _preference_records(
    session: Session,
    binding: MemoryContextBinding,
) -> tuple[MemoryContextRecord, ...]:
    rows = session.scalars(
        sa.select(MemoryPreferenceRecord)
        .where(
            MemoryPreferenceRecord.owner_id == binding.owner_id,
            MemoryPreferenceRecord.status == "active",
        )
        .order_by(
            MemoryPreferenceRecord.memory_key.asc(),
            MemoryPreferenceRecord.record_id.asc(),
        )
        .limit(_PREFERENCE_LIMIT)
    ).all()
    return tuple(
        _typed_record(
            row,
            kind=MemoryContextRecordKind.OWNER_PREFERENCE,
            priority=650,
            role=None,
        )
        for row in rows
    )


def _profile_records(
    session: Session,
    binding: MemoryContextBinding,
) -> tuple[MemoryContextRecord, ...]:
    if binding.relationship_role is not RelationshipRole.SELF:
        return ()
    rows = session.scalars(
        sa.select(PlayerProfileRecord)
        .where(
            PlayerProfileRecord.owner_id == binding.owner_id,
            PlayerProfileRecord.relationship_id == binding.relationship_id,
            PlayerProfileRecord.player_subject_id == binding.player_subject_id,
            PlayerProfileRecord.relationship_role == "self",
            PlayerProfileRecord.status == "active",
        )
        .order_by(
            PlayerProfileRecord.memory_key.asc(),
            PlayerProfileRecord.record_id.asc(),
        )
        .limit(_PROFILE_LIMIT)
    ).all()
    return tuple(
        _typed_record(
            row,
            kind=MemoryContextRecordKind.PLAYER_PROFILE,
            priority=600,
            role=RelationshipRole.SELF,
        )
        for row in rows
    )


def _review_records(
    session: Session,
    binding: MemoryContextBinding,
) -> tuple[MemoryContextRecord, ...]:
    rows = session.scalars(
        sa.select(ReviewMemoryRecord)
        .where(
            ReviewMemoryRecord.owner_id == binding.owner_id,
            ReviewMemoryRecord.relationship_id == binding.relationship_id,
            ReviewMemoryRecord.player_subject_id == binding.player_subject_id,
            ReviewMemoryRecord.relationship_role
            == binding.relationship_role.value,
            ReviewMemoryRecord.status == "active",
        )
        .order_by(
            ReviewMemoryRecord.memory_key.asc(),
            ReviewMemoryRecord.record_id.asc(),
        )
        .limit(_REVIEW_LIMIT)
    ).all()
    return tuple(
        _typed_record(
            row,
            kind=MemoryContextRecordKind.REVIEW_MEMORY,
            priority=500,
            role=binding.relationship_role,
        )
        for row in rows
    )


def _plan_records(
    session: Session,
    binding: MemoryContextBinding,
) -> tuple[MemoryContextRecord, ...]:
    if binding.relationship_role is not RelationshipRole.SELF:
        return ()
    row = session.scalar(
        sa.select(TrainingPlanRecord).where(
            TrainingPlanRecord.owner_id == binding.owner_id,
            TrainingPlanRecord.relationship_id == binding.relationship_id,
            TrainingPlanRecord.player_subject_id == binding.player_subject_id,
            TrainingPlanRecord.relationship_role == "self",
            TrainingPlanRecord.status == "active",
        )
    )
    if row is None:
        return ()
    return (
        MemoryContextRecord(
            kind=MemoryContextRecordKind.TRAINING_PLAN,
            record_id=row.plan_id,
            version=row.version,
            content_sha256=row.payload_sha256,
            content=_canonical_json(row.payload),
            priority=620,
            stable_order=f"training_plan:{row.version:010d}:{row.plan_id}",
            relationship_role=RelationshipRole.SELF,
        ),
    )


def _progress_records(
    session: Session,
    binding: MemoryContextBinding,
) -> tuple[MemoryContextRecord, ...]:
    if binding.relationship_role is not RelationshipRole.SELF:
        return ()
    plan_id = session.scalar(
        sa.select(TrainingPlanRecord.plan_id).where(
            TrainingPlanRecord.owner_id == binding.owner_id,
            TrainingPlanRecord.relationship_id == binding.relationship_id,
            TrainingPlanRecord.player_subject_id == binding.player_subject_id,
            TrainingPlanRecord.relationship_role == "self",
            TrainingPlanRecord.status == "active",
        )
    )
    if plan_id is None:
        return ()
    rows = session.scalars(
        sa.select(TrainingProgressRecord)
        .where(
            TrainingProgressRecord.owner_id == binding.owner_id,
            TrainingProgressRecord.plan_id == plan_id,
            TrainingProgressRecord.status == "active",
        )
        .order_by(
            TrainingProgressRecord.metric_key.asc(),
            TrainingProgressRecord.observed_at.desc(),
            TrainingProgressRecord.created_at.desc(),
            TrainingProgressRecord.progress_id.asc(),
        )
    ).all()
    latest = []
    seen: set[str] = set()
    for row in rows:
        if row.metric_key in seen:
            continue
        seen.add(row.metric_key)
        latest.append(row)
        if len(latest) == _PROGRESS_LIMIT:
            break
    values = []
    for row in latest:
        content = _canonical_json(
            {
                "metric_key": row.metric_key,
                "metric_value": row.metric_value,
                "observed_at": row.observed_at.isoformat(),
                "plan_id": str(row.plan_id),
            }
        )
        values.append(
            MemoryContextRecord(
                kind=MemoryContextRecordKind.TRAINING_PROGRESS,
                record_id=row.progress_id,
                version=1,
                content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                content=content,
                priority=550,
                stable_order=f"training_progress:{row.metric_key}:{row.progress_id}",
                relationship_role=RelationshipRole.SELF,
            )
        )
    return tuple(values)


def _typed_record(row, *, kind, priority, role):
    return MemoryContextRecord(
        kind=kind,
        record_id=row.record_id,
        version=row.version,
        content_sha256=row.payload_sha256,
        content=_canonical_json(
            {"memory_key": row.memory_key, "payload": row.payload}
        ),
        priority=priority,
        stable_order=f"{kind.value}:{row.memory_key}:{row.version:010d}",
        relationship_role=role,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


__all__ = ["MemoryContextRepositoryError", "PostgresMemoryContextRepository"]
