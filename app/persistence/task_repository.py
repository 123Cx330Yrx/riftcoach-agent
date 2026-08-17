from __future__ import annotations

import copy
from collections.abc import Callable
from uuid import UUID

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.persistence.task_record import ReviewTaskRecord
from app.tasks.models import (
    PendingReviewTask,
    ReviewTask,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskRepositoryCreateDisposition,
    TaskRepositoryCreateResult,
    TaskStatus,
)
from app.tasks.ports import TaskRepositoryError


SessionFactory = Callable[[], Session]
_ACTIVE_STATUSES = (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value)
# One PostgreSQL transaction-scoped namespace used only for short task-create
# transactions. Agent execution and future Worker claim never hold this lock.
_TASK_CREATE_ADVISORY_LOCK_ID = 593_231_842_001


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
                    task=_record_to_task(existing),
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
            task=_record_to_task(record),
        )

    def _get_one(self, statement: sa.Select[tuple[ReviewTaskRecord]]) -> ReviewTask | None:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(statement)
                    return None if record is None else _record_to_task(record)
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None


def _record_to_task(record: ReviewTaskRecord) -> ReviewTask:
    publication_status = (
        None
        if record.publication_status is None
        else TaskPublicationStatus(record.publication_status)
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


__all__ = ["PostgresTaskRepository"]
