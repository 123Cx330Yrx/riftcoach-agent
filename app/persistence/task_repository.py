from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.persistence.conversation_records import ConversationRecord
from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerAliasRecord,
    PlayerSubjectRecord,
)
from app.persistence.task_record import ReviewTaskRecord
from app.players.models import RelationshipRole, RoutingRegion
from app.tasks.fingerprint import compute_conversation_review_task_fingerprint
from app.tasks.models import (
    ConversationReviewExecutionTarget,
    ConversationReviewTaskBinding,
    PendingConversationReviewTask,
    PendingReviewTask,
    ReviewTask,
    SafeTaskCode,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskRepositoryCreateDisposition,
    TaskRepositoryCreateResult,
    TaskRepositoryDeleteDisposition,
    TaskRepositoryDeleteResult,
    TaskStatus,
    TaskTerminal,
    WorkerId,
)
from app.tasks.ports import TaskRepositoryError


SessionFactory = Callable[[], Session]
_ACTIVE_STATUSES = (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value)
# One PostgreSQL transaction-scoped namespace used only for short task-create
# transactions. Agent execution and Worker claim never use or hold this lock.
_TASK_CREATE_ADVISORY_LOCK_ID = 593_231_842_001
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)
_SAFE_TASK_CODE_ADAPTER = TypeAdapter(SafeTaskCode)


class PostgresTaskRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def create_or_replay(
        self,
        pending: PendingReviewTask,
        *,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult:
        if not isinstance(pending, PendingReviewTask):
            raise TypeError("pending must be a PendingReviewTask")
        if not isinstance(capacity, TaskCapacityPolicy):
            raise TypeError("capacity must be a TaskCapacityPolicy")

        try:
            with self._session_factory() as session:
                with session.begin():
                    session.execute(
                        sa.text(
                            "SELECT pg_advisory_xact_lock(:task_create_lock_id)"
                        ),
                        {"task_create_lock_id": _TASK_CREATE_ADVISORY_LOCK_ID},
                    )
                    result = self._create_or_replay_locked(
                        session,
                        pending=pending,
                        capacity=capacity,
                    )
                return result
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def create_conversation_bound_or_replay(
        self,
        pending: PendingConversationReviewTask,
        *,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult:
        if not isinstance(pending, PendingConversationReviewTask):
            raise TypeError("pending must be a PendingConversationReviewTask")
        if not isinstance(capacity, TaskCapacityPolicy):
            raise TypeError("capacity must be a TaskCapacityPolicy")

        try:
            with self._session_factory() as session:
                with session.begin():
                    session.execute(
                        sa.text(
                            "SELECT pg_advisory_xact_lock(:task_create_lock_id)"
                        ),
                        {"task_create_lock_id": _TASK_CREATE_ADVISORY_LOCK_ID},
                    )
                    result = self._create_conversation_bound_or_replay_locked(
                        session,
                        pending=pending,
                        capacity=capacity,
                    )
                return result
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def get_by_task_id(
        self,
        *,
        owner_id: str,
        task_id: UUID,
    ) -> ReviewTask | None:
        return self._get_one(
            sa.select(ReviewTaskRecord).where(
                ReviewTaskRecord.owner_id == owner_id,
                ReviewTaskRecord.task_id == task_id,
            )
        )

    def get_by_run_id(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> ReviewTask | None:
        return self._get_one(
            sa.select(ReviewTaskRecord).where(
                ReviewTaskRecord.owner_id == owner_id,
                ReviewTaskRecord.run_id == run_id,
            )
        )

    def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
    ) -> ReviewTask | None:
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_now = _as_utc(now)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.status == TaskStatus.QUEUED.value)
                        .order_by(
                            ReviewTaskRecord.created_at.asc(),
                            ReviewTaskRecord.task_id.asc(),
                        )
                        .limit(1)
                        .with_for_update(skip_locked=True)
                    )
                    if record is None:
                        return None
                    record.status = TaskStatus.RUNNING.value
                    record.worker_id = normalized_worker_id
                    record.claimed_at = normalized_now
                    record.updated_at = normalized_now
                    session.flush()
                    claimed = self._map_record(session, record)
                return claimed
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def succeed(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        terminal: TaskTerminal,
    ) -> bool:
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        if not isinstance(terminal, TaskTerminal):
            raise TypeError("terminal must be a TaskTerminal")
        return self._terminal_cas(
            task_id=task_id,
            worker_id=normalized_worker_id,
            expected_run_id=terminal.run_id,
            values={
                "status": TaskStatus.SUCCEEDED.value,
                "terminal_reason": terminal.terminal_reason,
                "publication_status": terminal.publication_status.value,
                "report_available": terminal.report_available,
                "trace_reference": terminal.trace_reference.model_dump(
                    mode="json"
                ),
                "receipt_reference": terminal.receipt_reference.model_dump(
                    mode="json"
                ),
                "artifact_reference": (
                    None
                    if terminal.artifact_reference is None
                    else terminal.artifact_reference.model_dump(mode="json")
                ),
            },
        )

    def fail(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        reason: str,
    ) -> bool:
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_reason = _validate_safe_task_code(reason)
        return self._terminal_cas(
            task_id=task_id,
            worker_id=normalized_worker_id,
            expected_run_id=None,
            values={
                "status": TaskStatus.FAILED.value,
                "terminal_reason": normalized_reason,
                "publication_status": None,
                "report_available": False,
                "trace_reference": None,
                "receipt_reference": None,
                "artifact_reference": None,
            },
        )

    def delete_terminal(
        self,
        *,
        owner_id: str,
        task_id: UUID,
    ) -> TaskRepositoryDeleteResult:
        """Hide a terminal task in one short owner-scoped transaction.

        File/Trace cleanup is deliberately performed by the caller only after
        this transaction commits.  Removing the SQL row first is the safety
        boundary that prevents a failed file cleanup from making the result
        visible again.
        """

        if not isinstance(owner_id, str) or not owner_id:
            raise TypeError("owner_id must be a non-empty string")
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(
                            ReviewTaskRecord.owner_id == owner_id,
                            ReviewTaskRecord.task_id == task_id,
                        )
                        .with_for_update()
                    )
                    if record is None:
                        return TaskRepositoryDeleteResult(
                            disposition=TaskRepositoryDeleteDisposition.NOT_FOUND,
                        )
                    if record.status in _ACTIVE_STATUSES:
                        return TaskRepositoryDeleteResult(
                            disposition=TaskRepositoryDeleteDisposition.ACTIVE_CONFLICT,
                            run_id=record.run_id,
                        )
                    run_id = record.run_id
                    session.delete(record)
                    session.flush()
                return TaskRepositoryDeleteResult(
                    disposition=TaskRepositoryDeleteDisposition.DELETED,
                    run_id=run_id,
                )
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def delete_expired_terminal(
        self,
        *,
        before: datetime,
        limit: int = 100,
    ) -> tuple[str, ...]:
        """Hide a bounded batch of old terminal rows in one short transaction."""

        normalized_before = _as_utc(before)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        try:
            with self._session_factory() as session:
                with session.begin():
                    records = list(
                        session.scalars(
                            sa.select(ReviewTaskRecord)
                            .where(
                                ReviewTaskRecord.status.in_(
                                    (
                                        TaskStatus.SUCCEEDED.value,
                                        TaskStatus.FAILED.value,
                                    )
                                ),
                                ReviewTaskRecord.finished_at.is_not(None),
                                ReviewTaskRecord.finished_at < normalized_before,
                            )
                            .order_by(ReviewTaskRecord.finished_at.asc())
                            .limit(limit)
                            .with_for_update(skip_locked=True)
                        )
                    )
                    run_ids = tuple(record.run_id for record in records)
                    for record in records:
                        session.delete(record)
                    session.flush()
                return run_ids
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def _create_or_replay_locked(
        self,
        session: Session,
        *,
        pending: PendingReviewTask,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult:
        existing = session.scalar(
            sa.select(ReviewTaskRecord).where(
                ReviewTaskRecord.owner_id == pending.owner_id,
                ReviewTaskRecord.idempotency_key == pending.idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint == pending.request_fingerprint:
                return TaskRepositoryCreateResult(
                    disposition=TaskRepositoryCreateDisposition.REPLAYED,
                    task=self._map_record(session, existing),
                )
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT,
            )

        owner_active = session.scalar(
            sa.select(sa.func.count())
            .select_from(ReviewTaskRecord)
            .where(
                ReviewTaskRecord.owner_id == pending.owner_id,
                ReviewTaskRecord.status.in_(_ACTIVE_STATUSES),
            )
        )
        if owner_active is None:
            raise TaskRepositoryError("task_repository_integrity_failed")
        if owner_active >= capacity.owner_active_limit:
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED,
            )

        global_active = session.scalar(
            sa.select(sa.func.count())
            .select_from(ReviewTaskRecord)
            .where(ReviewTaskRecord.status.in_(_ACTIVE_STATUSES))
        )
        if global_active is None:
            raise TaskRepositoryError("task_repository_integrity_failed")
        if global_active >= capacity.global_active_limit:
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED,
            )

        record = ReviewTaskRecord(
            task_id=pending.task_id,
            run_id=pending.run_id,
            task_kind=pending.task_kind,
            schema_version=pending.schema_version,
            owner_id=pending.owner_id,
            idempotency_key=pending.idempotency_key,
            request_fingerprint=pending.request_fingerprint,
            request_payload=copy.deepcopy(pending.request_payload),
            status=TaskStatus.QUEUED.value,
            worker_id=None,
            created_at=pending.created_at,
            updated_at=pending.created_at,
            claimed_at=None,
            finished_at=None,
            terminal_reason=None,
            publication_status=None,
            report_available=False,
            trace_reference=None,
            receipt_reference=None,
            artifact_reference=None,
        )
        session.add(record)
        session.flush()
        return TaskRepositoryCreateResult(
            disposition=TaskRepositoryCreateDisposition.CREATED,
            task=self._map_record(session, record),
        )

    def _create_conversation_bound_or_replay_locked(
        self,
        session: Session,
        *,
        pending: PendingConversationReviewTask,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult:
        identity = session.execute(
            sa.select(
                ConversationRecord.relationship_id,
                ConversationRecord.player_subject_id,
                ConversationRecord.relationship_role,
            ).where(
                ConversationRecord.owner_id == pending.owner_id,
                ConversationRecord.conversation_id == pending.conversation_id,
                ConversationRecord.status == "active",
            )
        ).one_or_none()
        if identity is None:
            return TaskRepositoryCreateResult(
                disposition=(
                    TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE
                )
            )

        relationship = session.scalar(
            sa.select(OwnerPlayerRelationshipRecord)
            .where(
                OwnerPlayerRelationshipRecord.owner_id == pending.owner_id,
                OwnerPlayerRelationshipRecord.relationship_id
                == identity.relationship_id,
                OwnerPlayerRelationshipRecord.player_subject_id
                == identity.player_subject_id,
                OwnerPlayerRelationshipRecord.relationship_role
                == identity.relationship_role,
            )
            .with_for_update()
        )
        if relationship is None or relationship.status != "active":
            return TaskRepositoryCreateResult(
                disposition=(
                    TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE
                )
            )

        conversation = session.scalar(
            sa.select(ConversationRecord)
            .where(
                ConversationRecord.owner_id == pending.owner_id,
                ConversationRecord.conversation_id == pending.conversation_id,
                ConversationRecord.relationship_id
                == relationship.relationship_id,
                ConversationRecord.player_subject_id
                == relationship.player_subject_id,
                ConversationRecord.relationship_role
                == relationship.relationship_role,
                ConversationRecord.status == "active",
            )
            .with_for_update()
        )
        if conversation is None:
            return TaskRepositoryCreateResult(
                disposition=(
                    TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE
                )
            )

        binding = ConversationReviewTaskBinding(
            conversation_id=conversation.conversation_id,
            relationship_id=conversation.relationship_id,
            player_subject_id=conversation.player_subject_id,
            relationship_role=RelationshipRole(conversation.relationship_role),
        )
        request_fingerprint = compute_conversation_review_task_fingerprint(
            owner_id=pending.owner_id,
            binding=binding,
            request_payload=pending.request_payload,
        )

        existing = session.scalar(
            sa.select(ReviewTaskRecord).where(
                ReviewTaskRecord.owner_id == pending.owner_id,
                ReviewTaskRecord.idempotency_key == pending.idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint == request_fingerprint:
                return TaskRepositoryCreateResult(
                    disposition=TaskRepositoryCreateDisposition.REPLAYED,
                    task=self._map_record(session, existing),
                )
            return TaskRepositoryCreateResult(
                disposition=TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT,
            )

        owner_active = session.scalar(
            sa.select(sa.func.count())
            .select_from(ReviewTaskRecord)
            .where(
                ReviewTaskRecord.owner_id == pending.owner_id,
                ReviewTaskRecord.status.in_(_ACTIVE_STATUSES),
            )
        )
        if owner_active is None:
            raise TaskRepositoryError("task_repository_integrity_failed")
        if owner_active >= capacity.owner_active_limit:
            return TaskRepositoryCreateResult(
                disposition=(
                    TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED
                )
            )

        global_active = session.scalar(
            sa.select(sa.func.count())
            .select_from(ReviewTaskRecord)
            .where(ReviewTaskRecord.status.in_(_ACTIVE_STATUSES))
        )
        if global_active is None:
            raise TaskRepositoryError("task_repository_integrity_failed")
        if global_active >= capacity.global_active_limit:
            return TaskRepositoryCreateResult(
                disposition=(
                    TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED
                )
            )

        record = ReviewTaskRecord(
            task_id=pending.task_id,
            run_id=pending.run_id,
            task_kind=pending.task_kind,
            schema_version=pending.schema_version,
            owner_id=pending.owner_id,
            idempotency_key=pending.idempotency_key,
            request_fingerprint=request_fingerprint,
            request_payload=copy.deepcopy(pending.request_payload),
            conversation_id=binding.conversation_id,
            relationship_id=binding.relationship_id,
            player_subject_id=binding.player_subject_id,
            relationship_role=binding.relationship_role.value,
            status=TaskStatus.QUEUED.value,
            worker_id=None,
            created_at=pending.created_at,
            updated_at=pending.created_at,
            claimed_at=None,
            finished_at=None,
            terminal_reason=None,
            publication_status=None,
            report_available=False,
            trace_reference=None,
            receipt_reference=None,
            artifact_reference=None,
        )
        session.add(record)
        session.flush()
        return TaskRepositoryCreateResult(
            disposition=TaskRepositoryCreateDisposition.CREATED,
            task=self._map_record(session, record),
        )

    def _get_one(self, statement: sa.Select[tuple[ReviewTaskRecord]]) -> ReviewTask | None:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(statement)
                    return None if record is None else self._map_record(
                        session,
                        record,
                    )
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    @staticmethod
    def _map_record(session: Session, record: ReviewTaskRecord) -> ReviewTask:
        execution_target = None
        if record.schema_version == "2.0":
            if record.player_subject_id is None:
                raise TaskRepositoryError("task_repository_integrity_failed")
            subject = session.scalar(
                sa.select(PlayerSubjectRecord).where(
                    PlayerSubjectRecord.player_subject_id
                    == record.player_subject_id,
                    PlayerSubjectRecord.game == "lol",
                )
            )
            if subject is None:
                raise TaskRepositoryError("task_repository_integrity_failed")
            alias = session.scalar(
                sa.select(PlayerAliasRecord)
                .where(
                    PlayerAliasRecord.player_subject_id
                    == record.player_subject_id,
                    PlayerAliasRecord.routing_region
                    == subject.current_routing_region,
                )
                .order_by(
                    PlayerAliasRecord.last_seen_at.desc(),
                    PlayerAliasRecord.player_alias_id.asc(),
                )
                .limit(1)
            )
            if alias is None:
                raise TaskRepositoryError("task_repository_integrity_failed")
            execution_target = ConversationReviewExecutionTarget(
                puuid=subject.puuid,
                routing_region=RoutingRegion(subject.current_routing_region),
                game_name=alias.game_name,
                tag_line=alias.tag_line,
            )
        return _record_to_task(record, execution_target=execution_target)

    def _terminal_cas(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        expected_run_id: str | None,
        values: dict[str, object],
    ) -> bool:
        try:
            with self._session_factory() as session:
                with session.begin():
                    terminal_time = sa.func.greatest(
                        sa.func.now(),
                        ReviewTaskRecord.claimed_at,
                    )
                    conditions = [
                        ReviewTaskRecord.task_id == task_id,
                        ReviewTaskRecord.status == TaskStatus.RUNNING.value,
                        ReviewTaskRecord.worker_id == worker_id,
                    ]
                    if expected_run_id is not None:
                        conditions.append(
                            ReviewTaskRecord.run_id == expected_run_id
                        )
                    result = session.execute(
                        sa.update(ReviewTaskRecord)
                        .where(*conditions)
                        .values(
                            **values,
                            updated_at=terminal_time,
                            finished_at=terminal_time,
                        )
                        .execution_options(synchronize_session=False)
                    )
                    if result.rowcount not in {0, 1}:
                        raise TaskRepositoryError(
                            "task_repository_integrity_failed"
                        )
                    updated = result.rowcount == 1
                return updated
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None


def _record_to_task(
    record: ReviewTaskRecord,
    *,
    execution_target: ConversationReviewExecutionTarget | None = None,
) -> ReviewTask:
    publication_status = (
        None
        if record.publication_status is None
        else TaskPublicationStatus(record.publication_status)
    )
    identity_values = (
        record.conversation_id,
        record.relationship_id,
        record.player_subject_id,
        record.relationship_role,
    )
    conversation_binding = None
    if any(value is not None for value in identity_values):
        if any(value is None for value in identity_values):
            raise ValueError("conversation identity must be all present or all absent")
        conversation_binding = ConversationReviewTaskBinding(
            conversation_id=record.conversation_id,
            relationship_id=record.relationship_id,
            player_subject_id=record.player_subject_id,
            relationship_role=RelationshipRole(record.relationship_role),
        )
    return ReviewTask(
        task_id=record.task_id,
        run_id=record.run_id,
        task_kind=record.task_kind,
        schema_version=record.schema_version,
        owner_id=record.owner_id,
        idempotency_key=record.idempotency_key,
        request_fingerprint=record.request_fingerprint,
        request_payload=copy.deepcopy(record.request_payload),
        conversation_binding=conversation_binding,
        execution_target=execution_target,
        status=TaskStatus(record.status),
        worker_id=record.worker_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        claimed_at=record.claimed_at,
        finished_at=record.finished_at,
        terminal_reason=record.terminal_reason,
        publication_status=publication_status,
        report_available=record.report_available,
        trace_reference=copy.deepcopy(record.trace_reference),
        receipt_reference=copy.deepcopy(record.receipt_reference),
        artifact_reference=copy.deepcopy(record.artifact_reference),
    )


def _validate_worker_id(value: str) -> str:
    try:
        return _WORKER_ID_ADAPTER.validate_python(value, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TypeError("worker_id must be a bounded safe identifier") from None


def _validate_safe_task_code(value: str) -> str:
    try:
        return _SAFE_TASK_CODE_ADAPTER.validate_python(value, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TypeError("reason must be a bounded safe code") from None


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("now must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = ["PostgresTaskRepository"]
