"""Strict, body-free contracts for the Stage 8 reliable task control plane.

Task lifecycle events are deliberately distinct from ``app.runtime`` events.
The former describe PostgreSQL ownership and recovery transitions; the latter
describe Provider, Tool and Harness facts inside one immutable Runtime Trace.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.harness.run_ids import normalize_run_id
from app.tasks.models import OwnerId, SafeTaskCode, TaskStatus, WorkerId


LeaseToken = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
]
EventIdentity = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
]
OperationIdentity = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    ),
]
CheckpointId = OperationIdentity


class ReliableTaskModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TaskLeasePolicy(ReliableTaskModel):
    lease_seconds: int = Field(default=120, ge=15, le=3600)
    heartbeat_seconds: int = Field(default=30, ge=1, le=1200)
    recovery_batch_size: int = Field(default=25, ge=1, le=100)
    max_recoveries: int = Field(default=3, ge=0, le=25)

    @model_validator(mode="after")
    def validate_heartbeat_window(self) -> Self:
        if self.heartbeat_seconds * 3 > self.lease_seconds:
            raise ValueError(
                "heartbeat_seconds must be at most one third of lease_seconds"
            )
        return self


class TaskLease(ReliableTaskModel):
    worker_id: WorkerId
    generation: int = Field(ge=1)
    token: LeaseToken = Field(exclude=True, repr=False)
    acquired_at: datetime
    heartbeat_at: datetime
    expires_at: datetime

    @field_validator("acquired_at", "heartbeat_at", "expires_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.heartbeat_at < self.acquired_at:
            raise ValueError("heartbeat_at must not precede acquired_at")
        if self.expires_at <= self.heartbeat_at:
            raise ValueError("expires_at must be later than heartbeat_at")
        return self

    @property
    def private_token(self) -> str:
        return self.token


class TaskCheckpointPhase(StrEnum):
    CLAIMED_SAFE = "claimed_safe"
    EXECUTION_STARTED = "execution_started"


class TaskCheckpointReference(ReliableTaskModel):
    schema_version: Literal["1.0"] = "1.0"
    checkpoint_id: CheckpointId
    run_id: str
    checkpoint_sequence: int = Field(ge=1)
    lease_generation: int = Field(ge=1)
    phase: TaskCheckpointPhase
    safe_to_replay: bool
    created_at: datetime

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_replay_boundary(self) -> Self:
        expected = self.phase is TaskCheckpointPhase.CLAIMED_SAFE
        if self.safe_to_replay is not expected:
            raise ValueError(
                "only a claimed_safe checkpoint may be safe_to_replay"
            )
        return self


class TaskCancelDisposition(StrEnum):
    CANCELLED = "cancelled"
    REQUESTED = "requested"
    ALREADY_REQUESTED = "already_requested"
    ALREADY_TERMINAL = "already_terminal"
    RECOVERY_REQUIRED = "recovery_required"


class TaskCancelResult(ReliableTaskModel):
    schema_version: Literal["1.0"] = "1.0"
    task_id: UUID
    disposition: TaskCancelDisposition
    status: TaskStatus

    @model_validator(mode="after")
    def validate_disposition_status(self) -> Self:
        allowed: dict[TaskCancelDisposition, frozenset[TaskStatus]] = {
            TaskCancelDisposition.CANCELLED: frozenset({TaskStatus.CANCELLED}),
            TaskCancelDisposition.REQUESTED: frozenset({TaskStatus.RUNNING}),
            TaskCancelDisposition.ALREADY_REQUESTED: frozenset(
                {TaskStatus.RUNNING}
            ),
            TaskCancelDisposition.ALREADY_TERMINAL: frozenset(
                {
                    TaskStatus.SUCCEEDED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                }
            ),
            TaskCancelDisposition.RECOVERY_REQUIRED: frozenset(
                {TaskStatus.RECOVERY_REQUIRED}
            ),
        }
        if self.status not in allowed[self.disposition]:
            raise ValueError("cancel disposition does not match task status")
        return self


class TaskHeartbeatDisposition(StrEnum):
    ACTIVE = "active"
    CANCEL_REQUESTED = "cancel_requested"
    LOST = "lost"


class TaskHeartbeatResult(ReliableTaskModel):
    task_id: UUID
    disposition: TaskHeartbeatDisposition
    lease_expires_at: datetime | None = None

    @field_validator("lease_expires_at")
    @classmethod
    def normalize_expiry(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        lost = self.disposition is TaskHeartbeatDisposition.LOST
        if lost != (self.lease_expires_at is None):
            raise ValueError("heartbeat disposition has an invalid expiry shape")
        return self


class TaskRecoveryStatus(StrEnum):
    CANCELLED = "cancelled"
    RECONCILED = "reconciled"
    REQUEUED = "requeued"
    RECOVERY_REQUIRED = "recovery_required"
    OWNERSHIP_LOST = "ownership_lost"


class TaskRecoveryResult(ReliableTaskModel):
    schema_version: Literal["1.0"] = "1.0"
    task_id: UUID
    run_id: str
    status: TaskRecoveryStatus
    reason: SafeTaskCode

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)


class TaskLifecycleEventKind(StrEnum):
    SNAPSHOT_IMPORTED = "snapshot_imported"
    CREATED = "created"
    CLAIMED = "claimed"
    HEARTBEAT = "heartbeat"
    CHECKPOINTED = "checkpointed"
    EXECUTION_STARTED = "execution_started"
    CANCEL_REQUESTED = "cancel_requested"
    RECOVERY_REQUEUED = "recovery_requeued"
    RECOVERY_REQUIRED = "recovery_required"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECONCILED = "reconciled"


_TERMINAL_EVENT_KINDS = frozenset(
    {
        TaskLifecycleEventKind.SUCCEEDED,
        TaskLifecycleEventKind.FAILED,
        TaskLifecycleEventKind.CANCELLED,
        TaskLifecycleEventKind.RECONCILED,
    }
)
_EXPECTED_STATUS: dict[TaskLifecycleEventKind, frozenset[TaskStatus]] = {
    TaskLifecycleEventKind.CREATED: frozenset({TaskStatus.QUEUED}),
    TaskLifecycleEventKind.CLAIMED: frozenset({TaskStatus.RUNNING}),
    TaskLifecycleEventKind.HEARTBEAT: frozenset({TaskStatus.RUNNING}),
    TaskLifecycleEventKind.CHECKPOINTED: frozenset({TaskStatus.RUNNING}),
    TaskLifecycleEventKind.EXECUTION_STARTED: frozenset({TaskStatus.RUNNING}),
    TaskLifecycleEventKind.CANCEL_REQUESTED: frozenset({TaskStatus.RUNNING}),
    TaskLifecycleEventKind.RECOVERY_REQUEUED: frozenset({TaskStatus.QUEUED}),
    TaskLifecycleEventKind.RECOVERY_REQUIRED: frozenset(
        {TaskStatus.RECOVERY_REQUIRED}
    ),
    TaskLifecycleEventKind.SUCCEEDED: frozenset({TaskStatus.SUCCEEDED}),
    TaskLifecycleEventKind.FAILED: frozenset({TaskStatus.FAILED}),
    TaskLifecycleEventKind.CANCELLED: frozenset({TaskStatus.CANCELLED}),
    TaskLifecycleEventKind.RECONCILED: frozenset({TaskStatus.SUCCEEDED}),
}


class TaskLifecycleEvent(ReliableTaskModel):
    event_schema_version: Literal["1.0"] = "1.0"
    event_cursor: int = Field(ge=1)
    event_identity: EventIdentity
    task_id: UUID
    run_id: str
    owner_id: OwnerId
    task_sequence: int = Field(ge=1)
    event_kind: TaskLifecycleEventKind
    status_after: TaskStatus
    lease_generation: int = Field(ge=0)
    worker_id: WorkerId | None = None
    operation_identity: OperationIdentity
    reason: SafeTaskCode | None = None
    checkpoint_reference: TaskCheckpointReference | None = None
    occurred_at: datetime

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.event_kind is TaskLifecycleEventKind.SNAPSHOT_IMPORTED:
            if self.task_sequence != 1:
                raise ValueError("snapshot_imported must be task sequence 1")
        elif self.status_after not in _EXPECTED_STATUS[self.event_kind]:
            raise ValueError("event kind does not match status_after")
        if self.event_kind is TaskLifecycleEventKind.CREATED:
            if self.lease_generation != 0 or self.worker_id is not None:
                raise ValueError("created event cannot contain lease ownership")
        if self.event_kind in {
            TaskLifecycleEventKind.CLAIMED,
            TaskLifecycleEventKind.HEARTBEAT,
            TaskLifecycleEventKind.CHECKPOINTED,
            TaskLifecycleEventKind.EXECUTION_STARTED,
            TaskLifecycleEventKind.CANCEL_REQUESTED,
            TaskLifecycleEventKind.RECOVERY_REQUEUED,
            TaskLifecycleEventKind.RECOVERY_REQUIRED,
            TaskLifecycleEventKind.SUCCEEDED,
            TaskLifecycleEventKind.FAILED,
            TaskLifecycleEventKind.RECONCILED,
        } and (self.lease_generation < 1 or self.worker_id is None):
            raise ValueError("owned event requires worker and lease generation")
        if self.event_kind is TaskLifecycleEventKind.CANCELLED:
            pre_claim = self.lease_generation == 0 and self.worker_id is None
            owned = self.lease_generation >= 1 and self.worker_id is not None
            if not (pre_claim or owned):
                raise ValueError("cancelled event has an invalid ownership shape")
        if self.event_kind in {
            TaskLifecycleEventKind.CHECKPOINTED,
            TaskLifecycleEventKind.EXECUTION_STARTED,
        }:
            if self.checkpoint_reference is None:
                raise ValueError("checkpoint event requires a checkpoint reference")
            if (
                self.checkpoint_reference.run_id != self.run_id
                or self.checkpoint_reference.lease_generation
                != self.lease_generation
            ):
                raise ValueError("checkpoint identity must match the event")
        elif self.checkpoint_reference is not None:
            raise ValueError("non-checkpoint event cannot contain a checkpoint")
        return self

    @classmethod
    def create(
        cls,
        *,
        event_cursor: int,
        task_sequence: int,
        task_id: UUID,
        run_id: str,
        owner_id: str,
        event_kind: TaskLifecycleEventKind,
        status_after: TaskStatus,
        lease_generation: int,
        operation_identity: str,
        occurred_at: datetime,
        worker_id: str | None = None,
        reason: str | None = None,
        checkpoint_reference: TaskCheckpointReference | None = None,
    ) -> "TaskLifecycleEvent":
        values = {
            "event_cursor": event_cursor,
            "event_identity": "0" * 64,
            "task_id": task_id,
            "run_id": run_id,
            "owner_id": owner_id,
            "task_sequence": task_sequence,
            "event_kind": event_kind,
            "status_after": status_after,
            "lease_generation": lease_generation,
            "worker_id": worker_id,
            "operation_identity": operation_identity,
            "reason": reason,
            "checkpoint_reference": checkpoint_reference,
            "occurred_at": occurred_at,
        }
        provisional = cls(**values)
        return provisional.model_copy(
            update={"event_identity": provisional.computed_identity()}
        )

    def computed_identity(self) -> str:
        checkpoint = self.checkpoint_reference
        components = (
            self.event_schema_version,
            str(self.task_id),
            self.run_id,
            self.owner_id,
            str(self.task_sequence),
            self.event_kind.value,
            self.status_after.value,
            str(self.lease_generation),
            self.worker_id or "",
            self.operation_identity,
            self.reason or "",
            "" if checkpoint is None else checkpoint.checkpoint_id,
            "" if checkpoint is None else str(checkpoint.checkpoint_sequence),
            "" if checkpoint is None else checkpoint.phase.value,
            (
                ""
                if checkpoint is None
                else "true"
                if checkpoint.safe_to_replay
                else "false"
            ),
            (
                ""
                if checkpoint is None
                else _canonical_timestamp(checkpoint.created_at)
            ),
            _canonical_timestamp(self.occurred_at),
        )
        encoded = "\x1f".join(components).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def has_valid_identity(self) -> bool:
        return self.event_identity == self.computed_identity()


class TaskLifecycleProjection(ReliableTaskModel):
    task_id: UUID
    run_id: str
    owner_id: OwnerId
    status: TaskStatus
    lease_generation: int = Field(ge=0)
    last_cursor: int = Field(ge=1)
    last_sequence: int = Field(ge=1)
    cancel_requested: bool = False
    terminal_seen: bool = False
    checkpoint_reference: TaskCheckpointReference | None = None


class TaskEventPage(ReliableTaskModel):
    schema_version: Literal["1.0"] = "1.0"
    after_cursor: int = Field(ge=0)
    next_cursor: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    has_more: bool
    events: tuple[TaskLifecycleEvent, ...] = ()

    @model_validator(mode="after")
    def validate_page(self) -> Self:
        if len(self.events) > self.limit:
            raise ValueError("event page exceeds its limit")
        if any(event.event_cursor <= self.after_cursor for event in self.events):
            raise ValueError("event page contains an old cursor")
        if any(not event.has_valid_identity() for event in self.events):
            raise ValueError("event page contains an invalid identity")
        if self.events:
            first = self.events[0]
            if self.after_cursor == 0 and first.task_sequence != 1:
                raise ValueError("initial event page must start at task sequence 1")
            for previous, current in zip(self.events, self.events[1:]):
                if current.event_cursor <= previous.event_cursor:
                    raise ValueError("event page cursor must strictly increase")
                if (
                    current.task_id != first.task_id
                    or current.run_id != first.run_id
                    or current.owner_id != first.owner_id
                ):
                    raise ValueError("event page identity tuple drifted")
                if current.task_sequence != previous.task_sequence + 1:
                    raise ValueError("event page task sequence must be contiguous")
        expected_cursor = (
            self.after_cursor if not self.events else self.events[-1].event_cursor
        )
        if self.next_cursor != expected_cursor:
            raise ValueError("next_cursor must identify the final returned event")
        return self


def project_task_lifecycle(
    events: tuple[TaskLifecycleEvent, ...] | list[TaskLifecycleEvent],
) -> TaskLifecycleProjection:
    """Replay one task's events while rejecting drift and late terminals."""

    if not isinstance(events, (tuple, list)) or not events:
        raise ValueError("task lifecycle projection requires events")
    first = events[0]
    if not isinstance(first, TaskLifecycleEvent):
        raise TypeError("events must contain TaskLifecycleEvent values")
    if first.event_kind not in {
        TaskLifecycleEventKind.CREATED,
        TaskLifecycleEventKind.SNAPSHOT_IMPORTED,
    }:
        raise ValueError("first task event must establish the lifecycle")

    task_id = first.task_id
    run_id = first.run_id
    owner_id = first.owner_id
    status: TaskStatus | None = None
    generation = 0
    last_cursor = 0
    checkpoint: TaskCheckpointReference | None = None
    cancel_requested = False
    terminal_seen = False

    for expected_sequence, current in enumerate(events, start=1):
        if not isinstance(current, TaskLifecycleEvent):
            raise TypeError("events must contain TaskLifecycleEvent values")
        if not current.has_valid_identity():
            raise ValueError("task event identity mismatch")
        if (
            current.task_id != task_id
            or current.run_id != run_id
            or current.owner_id != owner_id
        ):
            raise ValueError("task event identity tuple drifted")
        if current.task_sequence != expected_sequence:
            raise ValueError("task event sequence must be contiguous")
        if current.event_cursor <= last_cursor:
            raise ValueError("task event cursor must increase")
        if terminal_seen:
            raise ValueError("terminal task event must be final")

        _validate_transition(
            previous=status,
            event=current,
            previous_generation=generation,
        )
        status = current.status_after
        generation = current.lease_generation
        last_cursor = current.event_cursor
        if current.checkpoint_reference is not None:
            checkpoint = current.checkpoint_reference
        if current.event_kind is TaskLifecycleEventKind.CANCEL_REQUESTED:
            cancel_requested = True
        if current.event_kind in _TERMINAL_EVENT_KINDS:
            terminal_seen = True

    assert status is not None
    return TaskLifecycleProjection(
        task_id=task_id,
        run_id=run_id,
        owner_id=owner_id,
        status=status,
        lease_generation=generation,
        last_cursor=last_cursor,
        last_sequence=len(events),
        cancel_requested=cancel_requested,
        terminal_seen=terminal_seen,
        checkpoint_reference=checkpoint,
    )


def _validate_transition(
    *,
    previous: TaskStatus | None,
    event: TaskLifecycleEvent,
    previous_generation: int,
) -> None:
    if previous is None:
        return
    kind = event.event_kind
    allowed_previous: dict[TaskLifecycleEventKind, frozenset[TaskStatus]] = {
        TaskLifecycleEventKind.CLAIMED: frozenset({TaskStatus.QUEUED}),
        TaskLifecycleEventKind.HEARTBEAT: frozenset({TaskStatus.RUNNING}),
        TaskLifecycleEventKind.CHECKPOINTED: frozenset({TaskStatus.RUNNING}),
        TaskLifecycleEventKind.EXECUTION_STARTED: frozenset(
            {TaskStatus.RUNNING}
        ),
        TaskLifecycleEventKind.CANCEL_REQUESTED: frozenset(
            {TaskStatus.RUNNING}
        ),
        TaskLifecycleEventKind.RECOVERY_REQUEUED: frozenset(
            {TaskStatus.RUNNING}
        ),
        TaskLifecycleEventKind.RECOVERY_REQUIRED: frozenset(
            {TaskStatus.RUNNING}
        ),
        TaskLifecycleEventKind.SUCCEEDED: frozenset({TaskStatus.RUNNING}),
        TaskLifecycleEventKind.FAILED: frozenset(
            {TaskStatus.RUNNING, TaskStatus.RECOVERY_REQUIRED}
        ),
        TaskLifecycleEventKind.CANCELLED: frozenset(
            {
                TaskStatus.QUEUED,
                TaskStatus.RUNNING,
                TaskStatus.RECOVERY_REQUIRED,
            }
        ),
        TaskLifecycleEventKind.RECONCILED: frozenset(
            {TaskStatus.RUNNING, TaskStatus.RECOVERY_REQUIRED}
        ),
    }
    if kind in {
        TaskLifecycleEventKind.CREATED,
        TaskLifecycleEventKind.SNAPSHOT_IMPORTED,
    }:
        raise ValueError("lifecycle establishment event may only occur first")
    if previous not in allowed_previous[kind]:
        raise ValueError("task lifecycle transition is invalid")
    if kind is TaskLifecycleEventKind.CLAIMED:
        if event.lease_generation <= previous_generation:
            raise ValueError("claim must advance the lease generation")
    elif event.lease_generation != previous_generation:
        raise ValueError("non-claim event cannot change lease generation")


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="microseconds").replace(
        "+00:00",
        "Z",
    )


__all__ = [
    "TaskCancelDisposition",
    "TaskCancelResult",
    "TaskCheckpointPhase",
    "TaskCheckpointReference",
    "TaskEventPage",
    "TaskHeartbeatDisposition",
    "TaskHeartbeatResult",
    "TaskLease",
    "TaskLeasePolicy",
    "TaskLifecycleEvent",
    "TaskLifecycleEventKind",
    "TaskLifecycleProjection",
    "TaskRecoveryResult",
    "TaskRecoveryStatus",
    "project_task_lifecycle",
]
