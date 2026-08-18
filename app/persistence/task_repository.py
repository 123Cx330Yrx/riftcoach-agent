from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.persistence.task_record import ReviewTaskRecord
from app.tasks.models import (
    PendingReviewTask,
    ReviewTask,
    SafeTaskCode,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskRepositoryCreateDisposition,
    TaskRepositoryCreateResult,
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
                    claimed = _record_to_task(record)
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
