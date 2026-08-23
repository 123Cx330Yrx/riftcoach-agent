from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.lifecycle.models import (
    OwnerDataAffectedCounts,
    OwnerDataDeleteCommand,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerDataExport,
    OwnerDataExportRecord,
    OwnerDataExportSection,
    OwnerDataPurgeSummary,
    OwnerDataRetentionSummary,
)
from app.lifecycle.backup import OwnerRunReference
from app.lifecycle.service import OwnerDataLifecycleError
from app.persistence.conversation_records import ConversationMessageRecord, ConversationRecord
from app.persistence.memory_records import MemoryCandidateRecord
from app.persistence.owner_data_lifecycle_records import OwnerDataDeletionRecord
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord
from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)


class PostgresOwnerDataLifecycleRepository:
    def __init__(self, session_factory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def export_owner_data(
        self,
        *,
        owner_id: str,
        generated_at: datetime,
        limit_per_section: int,
    ) -> OwnerDataExport:
        if not isinstance(owner_id, str) or not owner_id:
            raise TypeError("owner_id must be non-empty")
        if type(limit_per_section) is not int or not 1 <= limit_per_section <= 500:
            raise TypeError("limit_per_section must be from 1 to 500")
        generated_at = _utc(generated_at)
        try:
            with self._session_factory() as session:
                with session.begin():
                    sections = (
                        _export_relationships(session, owner_id, limit_per_section),
                        _export_conversations(session, owner_id, limit_per_section),
                        _export_messages(session, owner_id, limit_per_section),
                        _export_candidates(session, owner_id, limit_per_section),
                        _export_typed_memories(session, owner_id, limit_per_section),
                        _export_training(session, owner_id, limit_per_section),
                        _export_tasks(session, owner_id, limit_per_section),
                    )
            return OwnerDataExport(
                owner_id=owner_id,
                generated_at=generated_at,
                policy_version="owner-data-export-v1",
                sections=sections,
                total_record_count=sum(len(section.records) for section in sections),
            )
        except OwnerDataLifecycleError:
            raise
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed") from None

    def hide_owner_data(
        self, command: OwnerDataDeleteCommand
    ) -> OwnerDataDeletionMarker:
        if not isinstance(command, OwnerDataDeleteCommand):
            raise TypeError("command must be an OwnerDataDeleteCommand")
        try:
            with self._session_factory() as session:
                with session.begin():
                    existing = session.scalar(
                        sa.select(OwnerDataDeletionRecord)
                        .where(
                            OwnerDataDeletionRecord.owner_id == command.owner_id,
                            OwnerDataDeletionRecord.idempotency_key
                            == command.idempotency_key,
                        )
                        .with_for_update()
                    )
                    if existing is not None:
                        if not _marker_matches(existing, command):
                            raise OwnerDataLifecycleError("idempotency_conflict")
                        return _marker(existing)

                    if command.conversation_id is not None:
                        conversation = session.scalar(
                            sa.select(ConversationRecord)
                            .where(
                                ConversationRecord.owner_id == command.owner_id,
                                ConversationRecord.conversation_id
                                == command.conversation_id,
                                ConversationRecord.status != "hidden",
                            )
                            .with_for_update()
                        )
                        if conversation is None:
                            raise OwnerDataLifecycleError("deletion_not_found")
                        counts = _hide_conversation_scope(
                            session, command, conversation=conversation
                        )
                    else:
                        relationship = session.scalar(
                            sa.select(OwnerPlayerRelationshipRecord)
                            .where(
                                OwnerPlayerRelationshipRecord.owner_id
                                == command.owner_id,
                                OwnerPlayerRelationshipRecord.relationship_id
                                == command.relationship_id,
                                OwnerPlayerRelationshipRecord.status == "active",
                                OwnerPlayerRelationshipRecord.hidden_at.is_(None),
                            )
                            .with_for_update()
                        )
                        if relationship is None:
                            raise OwnerDataLifecycleError("deletion_not_found")
                        counts = _hide_relationship_scope(
                            session, command, relationship=relationship
                        )

                    marker_id = uuid5(
                        NAMESPACE_URL,
                        f"riftcoach:owner-data-deletion:{command.owner_id}:"
                        f"{command.idempotency_key}",
                    )
                    record = OwnerDataDeletionRecord(
                        marker_id=marker_id,
                        schema_version="1.0",
                        owner_id=command.owner_id,
                        idempotency_key=command.idempotency_key,
                        scope=command.scope.value,
                        conversation_id=command.conversation_id,
                        relationship_id=command.relationship_id,
                        affected_counts=counts.model_dump(mode="json"),
                        status=OwnerDataDeletionStatus.CLEANUP_PENDING.value,
                        safe_reason=None,
                        created_at=command.requested_at,
                        updated_at=command.requested_at,
                        completed_at=None,
                    )
                    session.add(record)
                    session.flush()
                    return _marker(record)
        except OwnerDataLifecycleError:
            raise
        except IntegrityError:
            try:
                with self._session_factory() as session:
                    existing = session.scalar(
                        sa.select(OwnerDataDeletionRecord).where(
                            OwnerDataDeletionRecord.owner_id == command.owner_id,
                            OwnerDataDeletionRecord.idempotency_key
                            == command.idempotency_key,
                        )
                    )
                    if existing is not None and _marker_matches(existing, command):
                        return _marker(existing)
            except (SQLAlchemyError, TypeError, ValueError, ValidationError):
                pass
            raise OwnerDataLifecycleError("idempotency_conflict") from None
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed") from None

    def get_deletion_marker(
        self, *, owner_id: str, marker_id: UUID
    ) -> OwnerDataDeletionMarker | None:
        try:
            with self._session_factory() as session:
                record = session.scalar(
                    sa.select(OwnerDataDeletionRecord).where(
                        OwnerDataDeletionRecord.owner_id == owner_id,
                        OwnerDataDeletionRecord.marker_id == marker_id,
                    )
                )
                return None if record is None else _marker(record)
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed") from None

    def locate(self, marker: OwnerDataDeletionMarker) -> tuple[OwnerRunReference, ...]:
        """Locate run namespaces covered by an already-hidden owner marker.

        This is deliberately read-only and body-free.  Run directories are
        cleaned only after the lifecycle repository commits the hidden marker.
        """

        if not isinstance(marker, OwnerDataDeletionMarker):
            raise TypeError("marker must be an OwnerDataDeletionMarker")
        try:
            with self._session_factory() as session:
                query = sa.select(
                    ReviewTaskRecord.run_id,
                    ReviewTaskRecord.conversation_id,
                    ReviewTaskRecord.relationship_id,
                ).where(ReviewTaskRecord.owner_id == marker.owner_id)
                if marker.conversation_id is not None:
                    query = query.where(
                        ReviewTaskRecord.conversation_id == marker.conversation_id
                    )
                elif marker.relationship_id is not None:
                    query = query.where(
                        ReviewTaskRecord.relationship_id == marker.relationship_id
                    )
                else:
                    return ()
                rows = session.execute(query).all()
            return tuple(
                OwnerRunReference(
                    owner_id=marker.owner_id,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    relationship_id=relationship_id,
                )
                for run_id, conversation_id, relationship_id in rows
            )
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed") from None

    def complete_deletion(
        self, *, owner_id: str, marker_id: UUID, completed_at: datetime
    ) -> OwnerDataDeletionMarker:
        return self._update_marker(
            owner_id=owner_id,
            marker_id=marker_id,
            at=completed_at,
            complete=True,
            safe_reason=None,
        )

    def mark_cleanup_failed(
        self,
        *,
        owner_id: str,
        marker_id: UUID,
        safe_reason: str,
        updated_at: datetime,
    ) -> OwnerDataDeletionMarker:
        return self._update_marker(
            owner_id=owner_id,
            marker_id=marker_id,
            at=updated_at,
            complete=False,
            safe_reason=safe_reason,
        )

    def _update_marker(
        self,
        *,
        owner_id: str,
        marker_id: UUID,
        at: datetime,
        complete: bool,
        safe_reason: str | None,
    ) -> OwnerDataDeletionMarker:
        at = _utc(at)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(OwnerDataDeletionRecord)
                        .where(
                            OwnerDataDeletionRecord.owner_id == owner_id,
                            OwnerDataDeletionRecord.marker_id == marker_id,
                        )
                        .with_for_update()
                    )
                    if record is None:
                        raise OwnerDataLifecycleError("deletion_not_found")
                    if record.status == OwnerDataDeletionStatus.COMPLETE.value:
                        return _marker(record)
                    at = max(at, record.created_at, record.updated_at)
                    record.updated_at = at
                    if complete:
                        record.status = OwnerDataDeletionStatus.COMPLETE.value
                        record.safe_reason = None
                        record.completed_at = at
                    else:
                        record.safe_reason = safe_reason
                    session.flush()
                    return _marker(record)
        except OwnerDataLifecycleError:
            raise
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed") from None

    def apply_retention(
        self, *, evaluated_at: datetime, batch_size: int
    ) -> OwnerDataRetentionSummary:
        evaluated_at = _utc(evaluated_at)
        if type(batch_size) is not int or not 1 <= batch_size <= 1_000:
            raise TypeError("batch_size must be from 1 to 1000")
        expired_candidates = 0
        hidden = 0
        try:
            with self._session_factory() as session:
                with session.begin():
                    candidate_ids = _limited_ids(
                        session,
                        sa.select(MemoryCandidateRecord.candidate_id).where(
                            MemoryCandidateRecord.status == "pending",
                            MemoryCandidateRecord.hidden_at.is_(None),
                            MemoryCandidateRecord.expires_at <= evaluated_at,
                        ),
                        MemoryCandidateRecord.candidate_id,
                        batch_size,
                    )
                    if candidate_ids:
                        expired_candidates = _rowcount(
                            session.execute(
                                sa.update(MemoryCandidateRecord)
                                .where(MemoryCandidateRecord.candidate_id.in_(candidate_ids))
                                .values(
                                    status="expired",
                                    decision_actor_kind="system",
                                    decision_actor_id="retention",
                                    decision_reason_code="expired",
                                    decided_at=evaluated_at,
                                    updated_at=evaluated_at,
                                )
                            )
                        )

                    hidden += _retention_hide(
                        session,
                        ConversationMessageRecord,
                        ConversationMessageRecord.message_id,
                        sa.and_(
                            ConversationMessageRecord.hidden_at.is_(None),
                            ConversationMessageRecord.created_at
                            <= evaluated_at - timedelta(days=90),
                        ),
                        evaluated_at,
                        batch_size,
                    )
                    hidden += _retention_hide(
                        session,
                        MemoryCandidateRecord,
                        MemoryCandidateRecord.candidate_id,
                        sa.and_(
                            MemoryCandidateRecord.hidden_at.is_(None),
                            MemoryCandidateRecord.status.in_(("rejected", "expired")),
                            MemoryCandidateRecord.decided_at
                            <= evaluated_at - timedelta(days=30),
                        ),
                        evaluated_at,
                        batch_size,
                    )
                    for record_type in (
                        MemoryPreferenceRecord,
                        PlayerProfileRecord,
                    ):
                        hidden += _retention_hide(
                            session,
                            record_type,
                            record_type.record_id,
                            sa.and_(
                                record_type.hidden_at.is_(None),
                                record_type.status == "superseded",
                                record_type.updated_at
                                <= evaluated_at - timedelta(days=90),
                            ),
                            evaluated_at,
                            batch_size,
                        )
                    hidden += _retention_hide(
                        session,
                        ReviewMemoryRecord,
                        ReviewMemoryRecord.record_id,
                        sa.and_(
                            ReviewMemoryRecord.hidden_at.is_(None),
                            ReviewMemoryRecord.updated_at
                            <= evaluated_at - timedelta(days=365),
                        ),
                        evaluated_at,
                        batch_size,
                    )
                    hidden += _retention_hide(
                        session,
                        TrainingPlanRecord,
                        TrainingPlanRecord.plan_id,
                        sa.and_(
                            TrainingPlanRecord.hidden_at.is_(None),
                            TrainingPlanRecord.status.in_(("completed", "abandoned")),
                            TrainingPlanRecord.updated_at
                            <= evaluated_at - timedelta(days=365),
                        ),
                        evaluated_at,
                        batch_size,
                    )
                    hidden += _retention_hide_progress(
                        session, evaluated_at=evaluated_at, batch_size=batch_size
                    )
            return OwnerDataRetentionSummary(
                evaluated_at=evaluated_at,
                batch_size=batch_size,
                expired_candidates=expired_candidates,
                hidden_records=hidden,
            )
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed") from None

    def purge_hidden(
        self, *, evaluated_at: datetime, batch_size: int
    ) -> OwnerDataPurgeSummary:
        evaluated_at = _utc(evaluated_at)
        if type(batch_size) is not int or not 1 <= batch_size <= 1_000:
            raise TypeError("batch_size must be from 1 to 1000")
        cutoff = evaluated_at - timedelta(days=30)
        purged = 0
        blocked = 0
        definitions = (
            (TrainingProgressRecord, TrainingProgressRecord.progress_id),
            (TrainingPlanRecord, TrainingPlanRecord.plan_id),
            (MemoryPreferenceRecord, MemoryPreferenceRecord.record_id),
            (PlayerProfileRecord, PlayerProfileRecord.record_id),
            (ReviewMemoryRecord, ReviewMemoryRecord.record_id),
            (MemoryCandidateRecord, MemoryCandidateRecord.candidate_id),
            (ConversationMessageRecord, ConversationMessageRecord.message_id),
        )
        for record_type, id_column in definitions:
            count, was_blocked = self._purge_table(
                record_type=record_type,
                id_column=id_column,
                cutoff=cutoff,
                batch_size=batch_size,
            )
            purged += count
            blocked += was_blocked
        return OwnerDataPurgeSummary(
            evaluated_at=evaluated_at,
            batch_size=batch_size,
            purged_records=purged,
            blocked_records=blocked,
        )

    def _purge_table(self, *, record_type, id_column, cutoff, batch_size):
        ids: tuple[object, ...] = ()
        try:
            with self._session_factory() as session:
                with session.begin():
                    ids = _limited_ids(
                        session,
                        sa.select(id_column).where(record_type.hidden_at <= cutoff),
                        id_column,
                        batch_size,
                    )
                    if not ids:
                        return 0, 0
                    count = _rowcount(
                        session.execute(sa.delete(record_type).where(id_column.in_(ids)))
                    )
                    return count, 0
        except IntegrityError:
            return 0, len(ids)
        except SQLAlchemyError:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None


def _hide_conversation_scope(session: Session, command, *, conversation):
    at = command.requested_at
    conversation.status = "hidden"
    conversation.hidden_at = max(at, conversation.created_at)
    conversation.updated_at = max(at, conversation.updated_at, conversation.created_at)
    messages = _hide_rows(
        session,
        ConversationMessageRecord,
        sa.and_(
            ConversationMessageRecord.owner_id == command.owner_id,
            ConversationMessageRecord.conversation_id == conversation.conversation_id,
        ),
        at,
    )
    candidates = typed = plans = progress = 0
    if command.scope is OwnerDataDeleteScope.CONVERSATION_AND_DERIVED_MEMORY:
        candidates = _hide_rows(
            session,
            MemoryCandidateRecord,
            sa.and_(
                MemoryCandidateRecord.owner_id == command.owner_id,
                MemoryCandidateRecord.conversation_id == conversation.conversation_id,
            ),
            at,
        )
        for record_type in (
            MemoryPreferenceRecord,
            PlayerProfileRecord,
            ReviewMemoryRecord,
        ):
            typed += _hide_rows(
                session,
                record_type,
                sa.and_(
                    record_type.owner_id == command.owner_id,
                    record_type.source_conversation_id == conversation.conversation_id,
                ),
                at,
            )
        plans = _hide_rows(
            session,
            TrainingPlanRecord,
            sa.and_(
                TrainingPlanRecord.owner_id == command.owner_id,
                TrainingPlanRecord.source_conversation_id == conversation.conversation_id,
            ),
            at,
        )
        progress = _hide_rows(
            session,
            TrainingProgressRecord,
            sa.and_(
                TrainingProgressRecord.owner_id == command.owner_id,
                TrainingProgressRecord.source_conversation_id
                == conversation.conversation_id,
            ),
            at,
        )
    session.flush()
    return OwnerDataAffectedCounts(
        conversations=1,
        messages=messages,
        candidates=candidates,
        typed_memories=typed,
        training_plans=plans,
        training_progress=progress,
    )


def _hide_relationship_scope(session: Session, command, *, relationship):
    at = command.requested_at
    relationship.status = "hidden"
    relationship.hidden_at = max(at, relationship.created_at)
    relationship.updated_at = max(at, relationship.updated_at, relationship.created_at)
    conversation_ids = tuple(
        session.scalars(
            sa.select(ConversationRecord.conversation_id).where(
                ConversationRecord.owner_id == command.owner_id,
                ConversationRecord.relationship_id == relationship.relationship_id,
                ConversationRecord.status != "hidden",
            )
        )
    )
    conversations = _hide_conversations(
        session,
        owner_id=command.owner_id,
        relationship_id=relationship.relationship_id,
        at=at,
    )
    messages = 0
    if conversation_ids:
        messages = _hide_rows(
            session,
            ConversationMessageRecord,
            sa.and_(
                ConversationMessageRecord.owner_id == command.owner_id,
                ConversationMessageRecord.conversation_id.in_(conversation_ids),
            ),
            at,
        )
    candidates = _hide_rows(
        session,
        MemoryCandidateRecord,
        sa.and_(
            MemoryCandidateRecord.owner_id == command.owner_id,
            MemoryCandidateRecord.relationship_id == relationship.relationship_id,
            MemoryCandidateRecord.target_scope == "owner_player",
        ),
        at,
    )
    typed = 0
    for record_type in (PlayerProfileRecord, ReviewMemoryRecord):
        typed += _hide_rows(
            session,
            record_type,
            sa.and_(
                record_type.owner_id == command.owner_id,
                record_type.relationship_id == relationship.relationship_id,
            ),
            at,
        )
    plans = _hide_rows(
        session,
        TrainingPlanRecord,
        sa.and_(
            TrainingPlanRecord.owner_id == command.owner_id,
            TrainingPlanRecord.relationship_id == relationship.relationship_id,
        ),
        at,
    )
    progress = _hide_rows(
        session,
        TrainingProgressRecord,
        sa.and_(
            TrainingProgressRecord.owner_id == command.owner_id,
            TrainingProgressRecord.relationship_id == relationship.relationship_id,
        ),
        at,
    )
    session.flush()
    return OwnerDataAffectedCounts(
        relationships=1,
        conversations=conversations,
        messages=messages,
        candidates=candidates,
        typed_memories=typed,
        training_plans=plans,
        training_progress=progress,
    )


def _hide_conversations(session, *, owner_id, relationship_id, at):
    rows = session.scalars(
        sa.select(ConversationRecord)
        .where(
            ConversationRecord.owner_id == owner_id,
            ConversationRecord.relationship_id == relationship_id,
            ConversationRecord.status != "hidden",
        )
        .with_for_update()
    ).all()
    for row in rows:
        row.status = "hidden"
        row.hidden_at = max(at, row.created_at)
        row.updated_at = max(at, row.updated_at, row.created_at)
    return len(rows)


def _hide_rows(session, record_type, predicate, at):
    result = session.execute(
        sa.update(record_type)
        .where(predicate, record_type.hidden_at.is_(None))
        .values(hidden_at=at)
    )
    return _rowcount(result)


def _retention_hide(session, record_type, id_column, predicate, at, limit):
    ids = _limited_ids(session, sa.select(id_column).where(predicate), id_column, limit)
    if not ids:
        return 0
    return _rowcount(
        session.execute(
            sa.update(record_type).where(id_column.in_(ids)).values(hidden_at=at)
        )
    )


def _retention_hide_progress(session, *, evaluated_at, batch_size):
    ids = tuple(
        session.scalars(
            sa.select(TrainingProgressRecord.progress_id)
            .join(
                TrainingPlanRecord,
                TrainingPlanRecord.plan_id == TrainingProgressRecord.plan_id,
            )
            .where(
                TrainingProgressRecord.hidden_at.is_(None),
                TrainingPlanRecord.status.in_(("completed", "abandoned")),
                TrainingPlanRecord.updated_at
                <= evaluated_at - timedelta(days=365),
            )
            .order_by(TrainingProgressRecord.progress_id)
            .limit(batch_size)
        )
    )
    if not ids:
        return 0
    return _rowcount(
        session.execute(
            sa.update(TrainingProgressRecord)
            .where(TrainingProgressRecord.progress_id.in_(ids))
            .values(hidden_at=evaluated_at)
        )
    )


def _limited_ids(session, query, id_column, limit):
    return tuple(session.scalars(query.order_by(id_column).limit(limit)))


def _rowcount(result) -> int:
    value = result.rowcount
    return 0 if value is None or value < 0 else value


def _marker_matches(record, command):
    return (
        record.scope == command.scope.value
        and record.conversation_id == command.conversation_id
        and record.relationship_id == command.relationship_id
    )


def _marker(record) -> OwnerDataDeletionMarker:
    return OwnerDataDeletionMarker(
        marker_id=record.marker_id,
        owner_id=record.owner_id,
        idempotency_key=record.idempotency_key,
        scope=OwnerDataDeleteScope(record.scope),
        conversation_id=record.conversation_id,
        relationship_id=record.relationship_id,
        affected=OwnerDataAffectedCounts.model_validate(record.affected_counts),
        status=OwnerDataDeletionStatus(record.status),
        safe_reason=record.safe_reason,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


def _export_relationships(session, owner_id, limit):
    rows = _bounded(
        session,
        sa.select(OwnerPlayerRelationshipRecord)
        .where(
            OwnerPlayerRelationshipRecord.owner_id == owner_id,
            OwnerPlayerRelationshipRecord.status == "active",
            OwnerPlayerRelationshipRecord.hidden_at.is_(None),
        )
        .order_by(OwnerPlayerRelationshipRecord.relationship_id),
        limit,
    )
    return OwnerDataExportSection(
        name="relationships",
        records=tuple(
            OwnerDataExportRecord(
                record_kind="relationship",
                record_id=row.relationship_id,
                relationship_id=row.relationship_id,
                relationship_role=row.relationship_role,
                status=row.status,
                data={
                    "verification_status": row.verification_status,
                    "created_at": _iso(row.created_at),
                    "updated_at": _iso(row.updated_at),
                },
            )
            for row in rows
        ),
    )


def _export_conversations(session, owner_id, limit):
    rows = _bounded(
        session,
        sa.select(ConversationRecord)
        .where(
            ConversationRecord.owner_id == owner_id,
            ConversationRecord.status != "hidden",
            ConversationRecord.hidden_at.is_(None),
        )
        .order_by(ConversationRecord.conversation_id),
        limit,
    )
    return OwnerDataExportSection(
        name="conversations",
        records=tuple(
            OwnerDataExportRecord(
                record_kind="conversation",
                record_id=row.conversation_id,
                conversation_id=row.conversation_id,
                relationship_id=row.relationship_id,
                relationship_role=row.relationship_role,
                status=row.status,
                data={
                    "created_at": _iso(row.created_at),
                    "updated_at": _iso(row.updated_at),
                    "last_message_at": _optional_iso(row.last_message_at),
                },
            )
            for row in rows
        ),
    )


def _export_messages(session, owner_id, limit):
    rows = _bounded(
        session,
        sa.select(ConversationMessageRecord)
        .join(
            ConversationRecord,
            ConversationRecord.conversation_id
            == ConversationMessageRecord.conversation_id,
        )
        .where(
            ConversationMessageRecord.owner_id == owner_id,
            ConversationMessageRecord.hidden_at.is_(None),
            ConversationRecord.status != "hidden",
            ConversationRecord.hidden_at.is_(None),
        )
        .order_by(
            ConversationMessageRecord.conversation_id,
            ConversationMessageRecord.sequence_no,
        ),
        limit,
    )
    return OwnerDataExportSection(
        name="messages",
        records=tuple(
            OwnerDataExportRecord(
                record_kind="message",
                record_id=row.message_id,
                conversation_id=row.conversation_id,
                relationship_id=row.relationship_id,
                relationship_role=row.relationship_role,
                status="visible",
                data={
                    "sequence_no": row.sequence_no,
                    "role": row.role,
                    "content": row.content,
                    "content_sha256": row.content_sha256,
                    "source_task_id": _optional_uuid(row.source_task_id),
                    "source_run_id": row.source_run_id,
                    "created_at": _iso(row.created_at),
                },
            )
            for row in rows
        ),
    )


def _export_candidates(session, owner_id, limit):
    rows = _bounded(
        session,
        sa.select(MemoryCandidateRecord)
        .where(
            MemoryCandidateRecord.owner_id == owner_id,
            MemoryCandidateRecord.hidden_at.is_(None),
        )
        .order_by(MemoryCandidateRecord.created_at, MemoryCandidateRecord.candidate_id),
        limit,
    )
    return OwnerDataExportSection(
        name="memory_candidates",
        records=tuple(
            OwnerDataExportRecord(
                record_kind="memory_candidate",
                record_id=row.candidate_id,
                conversation_id=row.conversation_id,
                relationship_id=row.relationship_id,
                relationship_role=row.relationship_role,
                status=row.status,
                data={
                    "target_scope": row.target_scope,
                    "candidate_kind": row.candidate_kind,
                    "memory_key": row.memory_key,
                    "operation": row.operation,
                    "proposal_payload": row.proposal_payload,
                    "proposal_payload_sha256": row.proposal_payload_sha256,
                    "provenance_kind": row.provenance_kind,
                    "producer_id": row.producer_id,
                    "producer_version": row.producer_version,
                    "requires_confirmation": row.requires_confirmation,
                    "decision_actor_kind": row.decision_actor_kind,
                    "decision_reason_code": row.decision_reason_code,
                    "decided_at": _optional_iso(row.decided_at),
                    "source_task_id": _optional_uuid(row.source_task_id),
                    "source_run_id": row.source_run_id,
                    "source_artifact_sha256": row.source_artifact_sha256,
                },
            )
            for row in rows
        ),
    )


def _export_typed_memories(session, owner_id, limit):
    records = []
    for record_type, kind in (
        (MemoryPreferenceRecord, "owner_preference"),
        (PlayerProfileRecord, "player_profile"),
        (ReviewMemoryRecord, "review_memory"),
    ):
        rows = _bounded(
            session,
            sa.select(record_type)
            .where(record_type.owner_id == owner_id, record_type.hidden_at.is_(None))
            .order_by(record_type.created_at, record_type.record_id),
            limit,
        )
        records.extend(
            OwnerDataExportRecord(
                record_kind=kind,
                record_id=row.record_id,
                conversation_id=row.source_conversation_id,
                relationship_id=(
                    None if kind == "owner_preference" else row.relationship_id
                ),
                relationship_role=(
                    None if kind == "owner_preference" else row.relationship_role
                ),
                status=row.status,
                data={
                    "memory_key": row.memory_key,
                    "version": row.version,
                    "payload": row.payload,
                    "payload_sha256": row.payload_sha256,
                    "source_candidate_id": str(row.source_candidate_id),
                    "supersedes_record_id": _optional_uuid(row.supersedes_record_id),
                    "created_at": _iso(row.created_at),
                    "updated_at": _iso(row.updated_at),
                },
            )
            for row in rows
        )
    if len(records) > limit:
        raise OwnerDataLifecycleError("export_too_large")
    return OwnerDataExportSection(name="typed_memories", records=tuple(records))


def _export_training(session, owner_id, limit):
    plan_rows = _bounded(
        session,
        sa.select(TrainingPlanRecord)
        .where(
            TrainingPlanRecord.owner_id == owner_id,
            TrainingPlanRecord.hidden_at.is_(None),
        )
        .order_by(TrainingPlanRecord.created_at, TrainingPlanRecord.plan_id),
        limit,
    )
    progress_rows = _bounded(
        session,
        sa.select(TrainingProgressRecord)
        .where(
            TrainingProgressRecord.owner_id == owner_id,
            TrainingProgressRecord.hidden_at.is_(None),
        )
        .order_by(TrainingProgressRecord.created_at, TrainingProgressRecord.progress_id),
        limit,
    )
    records = [
        OwnerDataExportRecord(
            record_kind="training_plan",
            record_id=row.plan_id,
            conversation_id=row.source_conversation_id,
            relationship_id=row.relationship_id,
            relationship_role=row.relationship_role,
            status=row.status,
            data={
                "version": row.version,
                "payload": row.payload,
                "payload_sha256": row.payload_sha256,
                "source_candidate_id": str(row.source_candidate_id),
                "supersedes_plan_id": _optional_uuid(row.supersedes_plan_id),
                "created_at": _iso(row.created_at),
                "updated_at": _iso(row.updated_at),
            },
        )
        for row in plan_rows
    ]
    records.extend(
        OwnerDataExportRecord(
            record_kind="training_progress",
            record_id=row.progress_id,
            conversation_id=row.source_conversation_id,
            relationship_id=row.relationship_id,
            relationship_role=row.relationship_role,
            status=row.status,
            data={
                "plan_id": str(row.plan_id),
                "metric_key": row.metric_key,
                "metric_value": row.metric_value,
                "observed_at": _iso(row.observed_at),
                "source_candidate_id": str(row.source_candidate_id),
                "source_task_id": str(row.source_task_id),
                "source_run_id": row.source_run_id,
                "source_artifact_sha256": row.source_artifact_sha256,
                "supersedes_progress_id": _optional_uuid(
                    row.supersedes_progress_id
                ),
            },
        )
        for row in progress_rows
    )
    if len(records) > limit:
        raise OwnerDataLifecycleError("export_too_large")
    return OwnerDataExportSection(name="training", records=tuple(records))


def _export_tasks(session, owner_id, limit):
    rows = _bounded(
        session,
        sa.select(ReviewTaskRecord)
        .where(ReviewTaskRecord.owner_id == owner_id)
        .order_by(ReviewTaskRecord.created_at, ReviewTaskRecord.task_id),
        limit,
    )
    return OwnerDataExportSection(
        name="task_references",
        records=tuple(
            OwnerDataExportRecord(
                record_kind="task_reference",
                record_id=row.task_id,
                conversation_id=row.conversation_id,
                relationship_id=row.relationship_id,
                relationship_role=row.relationship_role,
                status=row.status,
                data={
                    "run_id": row.run_id,
                    "task_kind": row.task_kind,
                    "schema_version": row.schema_version,
                    "terminal_reason": row.terminal_reason,
                    "publication_status": row.publication_status,
                    "report_available": row.report_available,
                    "artifact_reference": row.artifact_reference,
                    "created_at": _iso(row.created_at),
                    "finished_at": _optional_iso(row.finished_at),
                },
            )
            for row in rows
        ),
    )


def _bounded(session, query, limit):
    rows = list(session.scalars(query.limit(limit + 1)))
    if len(rows) > limit:
        raise OwnerDataLifecycleError("export_too_large")
    return rows


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TypeError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _iso(value):
    return _utc(value).isoformat()


def _optional_iso(value):
    return None if value is None else _iso(value)


def _optional_uuid(value):
    return None if value is None else str(value)


__all__ = ["PostgresOwnerDataLifecycleRepository"]
