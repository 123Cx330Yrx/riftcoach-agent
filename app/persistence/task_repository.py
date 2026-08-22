from __future__ import annotations

import copy
import json
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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
from app.persistence.task_event_record import ReviewTaskEventRecord
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
from app.tasks.reliable_runtime import (
    TaskCancelDisposition,
    TaskCancelResult,
    TaskCheckpointPhase,
    TaskCheckpointReference,
    TaskEventPage,
    TaskHeartbeatDisposition,
    TaskHeartbeatResult,
    TaskLease,
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
)


SessionFactory = Callable[[], Session]
_ACTIVE_STATUSES = (
    TaskStatus.QUEUED.value,
    TaskStatus.RUNNING.value,
    TaskStatus.RECOVERY_REQUIRED.value,
)
# One PostgreSQL transaction-scoped namespace used only for short task-create
# transactions. Agent execution and Worker claim never use or hold this lock.
_TASK_CREATE_ADVISORY_LOCK_ID = 593_231_842_001
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)
_SAFE_TASK_CODE_ADAPTER = TypeAdapter(SafeTaskCode)
_EVENT_FIELD_UNSET = object()


@dataclass(frozen=True, slots=True)
class _RecoveryIdentity:
    task_id: UUID
    worker_id: str
    lease_generation: int
    lease_token: str = field(repr=False)
    now: datetime


class PostgresTaskRepository:
    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        lease_token_factory: Callable[[], str] | None = None,
    ) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        if lease_token_factory is not None and not callable(lease_token_factory):
            raise TypeError("lease_token_factory must be callable")
        self._session_factory = session_factory
        self._lease_token_factory = lease_token_factory or _default_lease_token

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
        lease_seconds: int = 120,
    ) -> ReviewTask | None:
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_now = _as_utc(now)
        normalized_lease_seconds = _validate_lease_seconds(lease_seconds)
        lease_token = _validate_lease_token(self._lease_token_factory())
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
                    generation = record.lease_generation + 1
                    checkpoint_sequence = record.checkpoint_sequence + 1
                    lease_expiry = normalized_now + timedelta(
                        seconds=normalized_lease_seconds
                    )
                    checkpoint = TaskCheckpointReference(
                        checkpoint_id=(
                            f"claimed-{generation}-{checkpoint_sequence}"
                        ),
                        run_id=record.run_id,
                        checkpoint_sequence=checkpoint_sequence,
                        lease_generation=generation,
                        phase=TaskCheckpointPhase.CLAIMED_SAFE,
                        safe_to_replay=True,
                        created_at=normalized_now,
                    )
                    record.status = TaskStatus.RUNNING.value
                    record.worker_id = normalized_worker_id
                    record.claimed_at = normalized_now
                    record.updated_at = normalized_now
                    record.lease_generation = generation
                    record.lease_token = lease_token
                    record.lease_expires_at = lease_expiry
                    record.heartbeat_at = normalized_now
                    record.checkpoint_sequence = checkpoint_sequence
                    record.checkpoint_reference = checkpoint.model_dump(mode="json")
                    record.recovery_required_at = None
                    record.recovery_reason = None
                    session.flush()
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.CLAIMED,
                        operation_identity=f"claim-{generation}",
                        occurred_at=normalized_now,
                    )
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.CHECKPOINTED,
                        operation_identity=checkpoint.checkpoint_id,
                        occurred_at=normalized_now,
                        checkpoint_reference=checkpoint,
                    )
                    claimed = self._map_record(session, record)
                return claimed
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def heartbeat(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        lease_seconds: int,
    ) -> TaskHeartbeatResult:
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_generation = _validate_lease_generation(lease_generation)
        normalized_token = _validate_lease_token(lease_token)
        normalized_now = _as_utc(now)
        normalized_seconds = _validate_lease_seconds(lease_seconds)
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == task_id)
                        .with_for_update()
                    )
                    if not _record_has_live_lease(
                        record,
                        worker_id=normalized_worker_id,
                        lease_generation=normalized_generation,
                        lease_token=normalized_token,
                        now=normalized_now,
                    ):
                        return TaskHeartbeatResult(
                            task_id=task_id,
                            disposition=TaskHeartbeatDisposition.LOST,
                        )
                    assert record is not None
                    lease_expiry = normalized_now + timedelta(
                        seconds=normalized_seconds
                    )
                    record.heartbeat_at = normalized_now
                    record.lease_expires_at = lease_expiry
                    record.updated_at = max(record.updated_at, normalized_now)
                    disposition = (
                        TaskHeartbeatDisposition.CANCEL_REQUESTED
                        if record.cancel_requested_at is not None
                        else TaskHeartbeatDisposition.ACTIVE
                    )
                    operation_identity = (
                        f"heartbeat-{normalized_generation}-"
                        f"{int(normalized_now.timestamp() * 1_000_000)}"
                    )
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.HEARTBEAT,
                        operation_identity=operation_identity,
                        occurred_at=normalized_now,
                    )
                return TaskHeartbeatResult(
                    task_id=task_id,
                    disposition=disposition,
                    lease_expires_at=lease_expiry,
                )
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def save_checkpoint(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        checkpoint_id: str,
        phase: TaskCheckpointPhase,
        now: datetime,
    ) -> bool:
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_generation = _validate_lease_generation(lease_generation)
        normalized_token = _validate_lease_token(lease_token)
        normalized_now = _as_utc(now)
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        if not isinstance(phase, TaskCheckpointPhase):
            raise TypeError("phase must be a TaskCheckpointPhase")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == task_id)
                        .with_for_update()
                    )
                    if not _record_has_live_lease(
                        record,
                        worker_id=normalized_worker_id,
                        lease_generation=normalized_generation,
                        lease_token=normalized_token,
                        now=normalized_now,
                    ) or record.cancel_requested_at is not None:
                        return False
                    assert record is not None
                    checkpoint = TaskCheckpointReference(
                        checkpoint_id=checkpoint_id,
                        run_id=record.run_id,
                        checkpoint_sequence=record.checkpoint_sequence + 1,
                        lease_generation=normalized_generation,
                        phase=phase,
                        safe_to_replay=(
                            phase is TaskCheckpointPhase.CLAIMED_SAFE
                        ),
                        created_at=normalized_now,
                    )
                    record.checkpoint_sequence = checkpoint.checkpoint_sequence
                    record.checkpoint_reference = checkpoint.model_dump(mode="json")
                    record.updated_at = max(record.updated_at, normalized_now)
                    self._append_event(
                        session,
                        record=record,
                        event_kind=(
                            TaskLifecycleEventKind.EXECUTION_STARTED
                            if phase is TaskCheckpointPhase.EXECUTION_STARTED
                            else TaskLifecycleEventKind.CHECKPOINTED
                        ),
                        operation_identity=checkpoint.checkpoint_id,
                        occurred_at=normalized_now,
                        checkpoint_reference=checkpoint,
                    )
                return True
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def request_cancel(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        request_id: str,
        reason: str,
        now: datetime,
    ) -> TaskCancelResult | None:
        if not isinstance(owner_id, str) or not owner_id:
            raise TypeError("owner_id must be a non-empty string")
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        normalized_request_id = _validate_operation_identity(request_id)
        normalized_reason = _validate_safe_task_code(reason)
        normalized_now = _as_utc(now)
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
                        return None
                    current = TaskStatus(record.status)
                    if current.is_terminal:
                        return TaskCancelResult(
                            task_id=task_id,
                            disposition=TaskCancelDisposition.ALREADY_TERMINAL,
                            status=current,
                        )
                    if current is TaskStatus.RECOVERY_REQUIRED:
                        return TaskCancelResult(
                            task_id=task_id,
                            disposition=TaskCancelDisposition.RECOVERY_REQUIRED,
                            status=current,
                        )
                    if record.cancel_request_id is not None:
                        return TaskCancelResult(
                            task_id=task_id,
                            disposition=TaskCancelDisposition.ALREADY_REQUESTED,
                            status=current,
                        )

                    request_time = max(record.created_at, normalized_now)
                    record.cancel_request_id = normalized_request_id
                    record.cancel_requested_at = request_time
                    record.cancel_reason = normalized_reason
                    record.updated_at = max(record.updated_at, request_time)
                    if current is TaskStatus.QUEUED:
                        record.status = TaskStatus.CANCELLED.value
                        record.finished_at = request_time
                        record.terminal_reason = normalized_reason
                        event_kind = TaskLifecycleEventKind.CANCELLED
                        disposition = TaskCancelDisposition.CANCELLED
                    else:
                        event_kind = TaskLifecycleEventKind.CANCEL_REQUESTED
                        disposition = TaskCancelDisposition.REQUESTED
                    self._append_event(
                        session,
                        record=record,
                        event_kind=event_kind,
                        operation_identity=normalized_request_id,
                        occurred_at=request_time,
                        reason=normalized_reason,
                    )
                return TaskCancelResult(
                    task_id=task_id,
                    disposition=disposition,
                    status=TaskStatus(record.status),
                )
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def cancel_running(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
    ) -> bool:
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_generation = _validate_lease_generation(lease_generation)
        normalized_token = _validate_lease_token(lease_token)
        normalized_now = _as_utc(now)
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == task_id)
                        .with_for_update()
                    )
                    if not _record_has_live_lease(
                        record,
                        worker_id=normalized_worker_id,
                        lease_generation=normalized_generation,
                        lease_token=normalized_token,
                        now=normalized_now,
                    ) or record.cancel_requested_at is None:
                        return False
                    assert record is not None
                    terminal_time = max(record.claimed_at, normalized_now)
                    reason = record.cancel_reason or "user_requested"
                    record.status = TaskStatus.CANCELLED.value
                    record.finished_at = terminal_time
                    record.updated_at = terminal_time
                    record.terminal_reason = reason
                    record.publication_status = None
                    record.report_available = False
                    record.trace_reference = None
                    record.receipt_reference = None
                    record.artifact_reference = None
                    record.lease_token = None
                    record.lease_expires_at = None
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.CANCELLED,
                        operation_identity=f"cancelled-{normalized_generation}",
                        occurred_at=terminal_time,
                        reason=reason,
                    )
                return True
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def read_events(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int = 0,
        limit: int = 50,
    ) -> TaskEventPage | None:
        if not isinstance(owner_id, str) or not owner_id:
            raise TypeError("owner_id must be a non-empty string")
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        if isinstance(after_cursor, bool) or not isinstance(after_cursor, int):
            raise TypeError("after_cursor must be an integer")
        if after_cursor < 0:
            raise ValueError("after_cursor must be non-negative")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            with self._session_factory() as session:
                with session.begin():
                    exists = session.scalar(
                        sa.select(ReviewTaskRecord.task_id).where(
                            ReviewTaskRecord.owner_id == owner_id,
                            ReviewTaskRecord.task_id == task_id,
                        )
                    )
                    if exists is None:
                        return None
                    records = tuple(
                        session.scalars(
                            sa.select(ReviewTaskEventRecord)
                            .where(
                                ReviewTaskEventRecord.owner_id == owner_id,
                                ReviewTaskEventRecord.task_id == task_id,
                                ReviewTaskEventRecord.event_cursor > after_cursor,
                            )
                            .order_by(ReviewTaskEventRecord.event_cursor.asc())
                            .limit(limit + 1)
                        )
                    )
                    has_more = len(records) > limit
                    events = tuple(
                        _event_record_to_model(record)
                        for record in records[:limit]
                    )
                return TaskEventPage(
                    after_cursor=after_cursor,
                    next_cursor=(
                        after_cursor if not events else events[-1].event_cursor
                    ),
                    limit=limit,
                    has_more=has_more,
                    events=events,
                )
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def list_expired_recovery_candidates(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[ReviewTask, ...]:
        normalized_now = _as_utc(now)
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        try:
            with self._session_factory() as session:
                with session.begin():
                    records = tuple(
                        session.scalars(
                            sa.select(ReviewTaskRecord)
                            .where(
                                ReviewTaskRecord.status
                                == TaskStatus.RUNNING.value,
                                ReviewTaskRecord.lease_expires_at.is_not(None),
                                ReviewTaskRecord.lease_expires_at
                                <= normalized_now,
                            )
                            .order_by(
                                ReviewTaskRecord.lease_expires_at.asc(),
                                ReviewTaskRecord.task_id.asc(),
                            )
                            .limit(limit)
                            .with_for_update(skip_locked=True)
                        )
                    )
                    candidates = tuple(
                        self._map_record(session, record) for record in records
                    )
                return candidates
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def cancel_expired(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
    ) -> bool:
        identity = _validate_recovery_identity(
            task_id=task_id,
            worker_id=worker_id,
            lease_generation=lease_generation,
            lease_token=lease_token,
            now=now,
        )
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == identity.task_id)
                        .with_for_update()
                    )
                    if not _record_has_expired_lease(record, identity=identity):
                        return False
                    assert record is not None
                    if record.cancel_requested_at is None:
                        return False
                    reason = record.cancel_reason or "user_requested"
                    terminal_time = max(record.claimed_at, identity.now)
                    record.status = TaskStatus.CANCELLED.value
                    record.finished_at = terminal_time
                    record.updated_at = terminal_time
                    record.terminal_reason = reason
                    record.publication_status = None
                    record.report_available = False
                    record.trace_reference = None
                    record.receipt_reference = None
                    record.artifact_reference = None
                    record.lease_token = None
                    record.lease_expires_at = None
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.CANCELLED,
                        operation_identity=(
                            f"recovery-cancelled-{identity.lease_generation}"
                        ),
                        occurred_at=terminal_time,
                        reason=reason,
                    )
                return True
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def reconcile_expired_success(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        terminal: TaskTerminal,
    ) -> bool:
        identity = _validate_recovery_identity(
            task_id=task_id,
            worker_id=worker_id,
            lease_generation=lease_generation,
            lease_token=lease_token,
            now=now,
        )
        if not isinstance(terminal, TaskTerminal):
            raise TypeError("terminal must be a TaskTerminal")
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == identity.task_id)
                        .with_for_update()
                    )
                    if not _record_has_expired_lease(record, identity=identity):
                        return False
                    assert record is not None
                    if (
                        record.cancel_requested_at is not None
                        or record.run_id != terminal.run_id
                    ):
                        return False
                    terminal_time = max(record.claimed_at, identity.now)
                    record.status = TaskStatus.SUCCEEDED.value
                    record.finished_at = terminal_time
                    record.updated_at = terminal_time
                    record.terminal_reason = terminal.terminal_reason
                    record.publication_status = terminal.publication_status.value
                    record.report_available = terminal.report_available
                    record.trace_reference = terminal.trace_reference.model_dump(
                        mode="json"
                    )
                    record.receipt_reference = (
                        terminal.receipt_reference.model_dump(mode="json")
                    )
                    record.artifact_reference = (
                        None
                        if terminal.artifact_reference is None
                        else terminal.artifact_reference.model_dump(mode="json")
                    )
                    record.lease_token = None
                    record.lease_expires_at = None
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.RECONCILED,
                        operation_identity=(
                            f"reconciled-{identity.lease_generation}"
                        ),
                        occurred_at=terminal_time,
                        reason="reconciled",
                    )
                return True
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def requeue_expired(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        max_recoveries: int,
    ) -> bool:
        identity = _validate_recovery_identity(
            task_id=task_id,
            worker_id=worker_id,
            lease_generation=lease_generation,
            lease_token=lease_token,
            now=now,
        )
        normalized_max = _validate_max_recoveries(max_recoveries)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == identity.task_id)
                        .with_for_update()
                    )
                    if not _record_has_expired_lease(record, identity=identity):
                        return False
                    assert record is not None
                    checkpoint = (
                        None
                        if record.checkpoint_reference is None
                        else _checkpoint_from_storage(record.checkpoint_reference)
                    )
                    if (
                        record.cancel_requested_at is not None
                        or checkpoint is None
                        or checkpoint.phase is not TaskCheckpointPhase.CLAIMED_SAFE
                        or not checkpoint.safe_to_replay
                        or checkpoint.lease_generation
                        != identity.lease_generation
                        or record.recovery_count >= normalized_max
                    ):
                        return False
                    previous_worker_id = record.worker_id
                    record.status = TaskStatus.QUEUED.value
                    record.worker_id = None
                    record.claimed_at = None
                    record.heartbeat_at = None
                    record.lease_token = None
                    record.lease_expires_at = None
                    record.recovery_count += 1
                    record.recovery_required_at = None
                    record.recovery_reason = None
                    record.updated_at = max(record.created_at, identity.now)
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.RECOVERY_REQUEUED,
                        operation_identity=(
                            f"requeue-{identity.lease_generation}-"
                            f"{record.recovery_count}"
                        ),
                        occurred_at=record.updated_at,
                        reason="claimed_safe",
                        worker_id_override=previous_worker_id,
                    )
                return True
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def mark_recovery_required(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        reason: str,
    ) -> bool:
        identity = _validate_recovery_identity(
            task_id=task_id,
            worker_id=worker_id,
            lease_generation=lease_generation,
            lease_token=lease_token,
            now=now,
        )
        normalized_reason = _validate_safe_task_code(reason)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == identity.task_id)
                        .with_for_update()
                    )
                    if not _record_has_expired_lease(record, identity=identity):
                        return False
                    assert record is not None
                    if record.cancel_requested_at is not None:
                        return False
                    required_at = max(record.claimed_at, identity.now)
                    record.status = TaskStatus.RECOVERY_REQUIRED.value
                    record.updated_at = required_at
                    record.recovery_required_at = required_at
                    record.recovery_reason = normalized_reason
                    record.lease_token = None
                    record.lease_expires_at = None
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.RECOVERY_REQUIRED,
                        operation_identity=(
                            f"recovery-required-{identity.lease_generation}"
                        ),
                        occurred_at=required_at,
                        reason=normalized_reason,
                    )
                return True
        except TaskRepositoryError:
            raise
        except SQLAlchemyError:
            raise TaskRepositoryError("task_repository_unavailable") from None
        except (TypeError, ValueError, ValidationError):
            raise TaskRepositoryError("task_repository_integrity_failed") from None

    def fail_recovery_required(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        now: datetime,
        reason: str,
    ) -> bool:
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_generation = _validate_lease_generation(lease_generation)
        normalized_now = _as_utc(now)
        normalized_reason = _validate_safe_task_code(reason)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == task_id)
                        .with_for_update()
                    )
                    if (
                        record is None
                        or record.status
                        != TaskStatus.RECOVERY_REQUIRED.value
                        or record.worker_id != normalized_worker_id
                        or record.lease_generation != normalized_generation
                        or record.lease_token is not None
                    ):
                        return False
                    terminal_time = max(record.claimed_at, normalized_now)
                    record.status = TaskStatus.FAILED.value
                    record.finished_at = terminal_time
                    record.updated_at = terminal_time
                    record.terminal_reason = normalized_reason
                    record.publication_status = None
                    record.report_available = False
                    record.trace_reference = None
                    record.receipt_reference = None
                    record.artifact_reference = None
                    record.recovery_required_at = None
                    record.recovery_reason = None
                    self._append_event(
                        session,
                        record=record,
                        event_kind=TaskLifecycleEventKind.FAILED,
                        operation_identity=(
                            f"manual-failed-{normalized_generation}"
                        ),
                        occurred_at=terminal_time,
                        reason=normalized_reason,
                    )
                return True
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
        lease_generation: int,
        lease_token: str,
        now: datetime,
        terminal: TaskTerminal,
    ) -> bool:
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_generation = _validate_lease_generation(lease_generation)
        normalized_token = _validate_lease_token(lease_token)
        normalized_now = _as_utc(now)
        if not isinstance(terminal, TaskTerminal):
            raise TypeError("terminal must be a TaskTerminal")
        return self._terminal_cas(
            task_id=task_id,
            worker_id=normalized_worker_id,
            lease_generation=normalized_generation,
            lease_token=normalized_token,
            now=normalized_now,
            expected_run_id=terminal.run_id,
            event_kind=TaskLifecycleEventKind.SUCCEEDED,
            operation_identity=f"succeeded-{normalized_generation}",
            event_reason=terminal.terminal_reason,
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
        lease_generation: int,
        lease_token: str,
        now: datetime,
        reason: str,
    ) -> bool:
        if not isinstance(task_id, UUID):
            raise TypeError("task_id must be a UUID")
        normalized_worker_id = _validate_worker_id(worker_id)
        normalized_generation = _validate_lease_generation(lease_generation)
        normalized_token = _validate_lease_token(lease_token)
        normalized_now = _as_utc(now)
        normalized_reason = _validate_safe_task_code(reason)
        return self._terminal_cas(
            task_id=task_id,
            worker_id=normalized_worker_id,
            lease_generation=normalized_generation,
            lease_token=normalized_token,
            now=normalized_now,
            expected_run_id=None,
            event_kind=TaskLifecycleEventKind.FAILED,
            operation_identity=f"failed-{normalized_generation}",
            event_reason=normalized_reason,
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
                                        TaskStatus.CANCELLED.value,
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
            lease_generation=0,
            lease_token=None,
            lease_expires_at=None,
            heartbeat_at=None,
            cancel_request_id=None,
            cancel_requested_at=None,
            cancel_reason=None,
            checkpoint_sequence=0,
            checkpoint_reference=None,
            recovery_count=0,
            recovery_required_at=None,
            recovery_reason=None,
            terminal_reason=None,
            publication_status=None,
            report_available=False,
            trace_reference=None,
            receipt_reference=None,
            artifact_reference=None,
        )
        session.add(record)
        session.flush()
        self._append_event(
            session,
            record=record,
            event_kind=TaskLifecycleEventKind.CREATED,
            operation_identity="created",
            occurred_at=pending.created_at,
        )
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
            lease_generation=0,
            lease_token=None,
            lease_expires_at=None,
            heartbeat_at=None,
            cancel_request_id=None,
            cancel_requested_at=None,
            cancel_reason=None,
            checkpoint_sequence=0,
            checkpoint_reference=None,
            recovery_count=0,
            recovery_required_at=None,
            recovery_reason=None,
            terminal_reason=None,
            publication_status=None,
            report_available=False,
            trace_reference=None,
            receipt_reference=None,
            artifact_reference=None,
        )
        session.add(record)
        session.flush()
        self._append_event(
            session,
            record=record,
            event_kind=TaskLifecycleEventKind.CREATED,
            operation_identity="created",
            occurred_at=pending.created_at,
        )
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

    @staticmethod
    def _append_event(
        session: Session,
        *,
        record: ReviewTaskRecord,
        event_kind: TaskLifecycleEventKind,
        operation_identity: str,
        occurred_at: datetime,
        reason: str | None = None,
        checkpoint_reference: TaskCheckpointReference | None = None,
        worker_id_override: str | None | object = _EVENT_FIELD_UNSET,
    ) -> TaskLifecycleEvent:
        event_worker_id = (
            record.worker_id
            if worker_id_override is _EVENT_FIELD_UNSET
            else worker_id_override
        )
        existing = session.scalar(
            sa.select(ReviewTaskEventRecord).where(
                ReviewTaskEventRecord.task_id == record.task_id,
                ReviewTaskEventRecord.operation_identity
                == operation_identity,
            )
        )
        if existing is not None:
            existing_event = _event_record_to_model(existing)
            expected_event = TaskLifecycleEvent.create(
                event_cursor=existing_event.event_cursor,
                task_sequence=existing_event.task_sequence,
                task_id=record.task_id,
                run_id=record.run_id,
                owner_id=record.owner_id,
                event_kind=event_kind,
                status_after=TaskStatus(record.status),
                lease_generation=record.lease_generation,
                worker_id=event_worker_id,
                operation_identity=operation_identity,
                reason=reason,
                checkpoint_reference=checkpoint_reference,
                occurred_at=occurred_at,
            )
            if existing_event != expected_event:
                raise TaskRepositoryError("task_repository_integrity_failed")
            return existing_event
        latest_sequence = session.scalar(
            sa.select(sa.func.max(ReviewTaskEventRecord.task_sequence)).where(
                ReviewTaskEventRecord.task_id == record.task_id
            )
        )
        task_sequence = (latest_sequence or 0) + 1
        event = TaskLifecycleEvent.create(
            event_cursor=1,
            task_sequence=task_sequence,
            task_id=record.task_id,
            run_id=record.run_id,
            owner_id=record.owner_id,
            event_kind=event_kind,
            status_after=TaskStatus(record.status),
            lease_generation=record.lease_generation,
            worker_id=event_worker_id,
            operation_identity=operation_identity,
            reason=reason,
            checkpoint_reference=checkpoint_reference,
            occurred_at=occurred_at,
        )
        event_record = ReviewTaskEventRecord(
            event_identity=event.event_identity,
            task_id=event.task_id,
            run_id=event.run_id,
            owner_id=event.owner_id,
            task_sequence=event.task_sequence,
            event_kind=event.event_kind.value,
            status_after=event.status_after.value,
            lease_generation=event.lease_generation,
            worker_id=event.worker_id,
            operation_identity=event.operation_identity,
            reason=event.reason,
            checkpoint_reference=(
                None
                if event.checkpoint_reference is None
                else event.checkpoint_reference.model_dump(mode="json")
            ),
            occurred_at=event.occurred_at,
        )
        session.add(event_record)
        session.flush()
        return _event_record_to_model(event_record)

    def _terminal_cas(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        expected_run_id: str | None,
        event_kind: TaskLifecycleEventKind,
        operation_identity: str,
        event_reason: str,
        values: dict[str, object],
    ) -> bool:
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(ReviewTaskRecord.task_id == task_id)
                        .with_for_update()
                    )
                    if not _record_has_live_lease(
                        record,
                        worker_id=worker_id,
                        lease_generation=lease_generation,
                        lease_token=lease_token,
                        now=now,
                    ) or record.cancel_requested_at is not None:
                        return False
                    assert record is not None
                    if expected_run_id is not None and (
                        record.run_id != expected_run_id
                    ):
                        return False
                    terminal_time = max(record.claimed_at, now)
                    for key, value in values.items():
                        setattr(record, key, value)
                    record.updated_at = terminal_time
                    record.finished_at = terminal_time
                    record.lease_token = None
                    record.lease_expires_at = None
                    self._append_event(
                        session,
                        record=record,
                        event_kind=event_kind,
                        operation_identity=operation_identity,
                        occurred_at=terminal_time,
                        reason=event_reason,
                    )
                return True
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
    lease_generation = record.lease_generation or 0
    lease = None
    if record.lease_token is not None:
        if (
            record.worker_id is None
            or record.claimed_at is None
            or record.heartbeat_at is None
            or record.lease_expires_at is None
        ):
            raise ValueError("live lease record is incomplete")
        lease = TaskLease(
            worker_id=record.worker_id,
            generation=lease_generation,
            token=record.lease_token,
            acquired_at=record.claimed_at,
            heartbeat_at=record.heartbeat_at,
            expires_at=record.lease_expires_at,
        )
    checkpoint_reference = (
        None
        if record.checkpoint_reference is None
        else _checkpoint_from_storage(record.checkpoint_reference)
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
        lease_generation=lease_generation,
        lease=lease,
        cancel_request_id=record.cancel_request_id,
        cancel_requested_at=record.cancel_requested_at,
        cancel_reason=record.cancel_reason,
        checkpoint_sequence=record.checkpoint_sequence or 0,
        checkpoint_reference=checkpoint_reference,
        recovery_count=record.recovery_count or 0,
        recovery_required_at=record.recovery_required_at,
        recovery_reason=record.recovery_reason,
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


def _validate_lease_generation(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TypeError("lease_generation must be a positive integer")
    return value


def _validate_lease_token(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TypeError("lease_token must be a 64-character lowercase hex value")
    return value


def _validate_lease_seconds(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("lease_seconds must be an integer")
    if not 15 <= value <= 3600:
        raise ValueError("lease_seconds must be between 15 and 3600")
    return value


def _validate_max_recoveries(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_recoveries must be an integer")
    if not 0 <= value <= 25:
        raise ValueError("max_recoveries must be between 0 and 25")
    return value


def _validate_recovery_identity(
    *,
    task_id: UUID,
    worker_id: str,
    lease_generation: int,
    lease_token: str,
    now: datetime,
) -> _RecoveryIdentity:
    if not isinstance(task_id, UUID):
        raise TypeError("task_id must be a UUID")
    return _RecoveryIdentity(
        task_id=task_id,
        worker_id=_validate_worker_id(worker_id),
        lease_generation=_validate_lease_generation(lease_generation),
        lease_token=_validate_lease_token(lease_token),
        now=_as_utc(now),
    )


def _validate_operation_identity(value: str) -> str:
    try:
        event = TaskLifecycleEvent.create(
            event_cursor=1,
            task_sequence=1,
            task_id=UUID("00000000-0000-4000-8000-000000000001"),
            run_id="operation_identity_validation",
            owner_id="operation-identity-validation",
            event_kind=TaskLifecycleEventKind.CREATED,
            status_after=TaskStatus.QUEUED,
            lease_generation=0,
            operation_identity=value,
            occurred_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
    except (TypeError, ValueError, ValidationError):
        raise TypeError("operation identity must be a bounded safe identifier") from None
    return event.operation_identity


def _record_has_live_lease(
    record: ReviewTaskRecord | None,
    *,
    worker_id: str,
    lease_generation: int,
    lease_token: str,
    now: datetime,
) -> bool:
    return bool(
        record is not None
        and record.status == TaskStatus.RUNNING.value
        and record.worker_id == worker_id
        and record.lease_generation == lease_generation
        and secrets.compare_digest(record.lease_token or "", lease_token)
        and record.lease_expires_at is not None
        and record.lease_expires_at > now
    )


def _record_has_expired_lease(
    record: ReviewTaskRecord | None,
    *,
    identity: _RecoveryIdentity,
) -> bool:
    return bool(
        record is not None
        and record.status == TaskStatus.RUNNING.value
        and record.worker_id == identity.worker_id
        and record.lease_generation == identity.lease_generation
        and secrets.compare_digest(
            record.lease_token or "",
            identity.lease_token,
        )
        and record.lease_expires_at is not None
        and record.lease_expires_at <= identity.now
    )


def _event_record_to_model(record: ReviewTaskEventRecord) -> TaskLifecycleEvent:
    event = TaskLifecycleEvent(
        event_cursor=record.event_cursor,
        event_identity=record.event_identity,
        task_id=record.task_id,
        run_id=record.run_id,
        owner_id=record.owner_id,
        task_sequence=record.task_sequence,
        event_kind=TaskLifecycleEventKind(record.event_kind),
        status_after=TaskStatus(record.status_after),
        lease_generation=record.lease_generation,
        worker_id=record.worker_id,
        operation_identity=record.operation_identity,
        reason=record.reason,
        checkpoint_reference=(
            None
            if record.checkpoint_reference is None
            else _checkpoint_from_storage(record.checkpoint_reference)
        ),
        occurred_at=record.occurred_at,
    )
    if not event.has_valid_identity():
        raise TaskRepositoryError("task_repository_integrity_failed")
    return event


def _default_lease_token() -> str:
    return secrets.token_hex(32)


def _checkpoint_from_storage(
    value: object,
) -> TaskCheckpointReference:
    """Parse JSONB checkpoint data through the strict JSON wire contract."""

    try:
        # psycopg may expose JSONB values as its Jsonb wrapper in some result
        # paths; unwrap it without changing the strict JSON contract.
        value = getattr(value, "obj", value)
        if isinstance(value, str):
            payload = value
        elif isinstance(value, Mapping):
            payload = json.dumps(
                dict(value), separators=(",", ":"), ensure_ascii=False
            )
        else:
            raise TypeError("checkpoint_reference must be JSON object data")
        return TaskCheckpointReference.model_validate_json(payload)
    except (TypeError, ValueError, ValidationError):
        raise ValueError("checkpoint_reference has an invalid JSON shape") from None


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("now must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = ["PostgresTaskRepository"]
