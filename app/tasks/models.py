from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.harness.run_ids import normalize_run_id
from app.product.recent_review import RecentReviewProductRequest


_OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$"
_IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_WORKER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_SAFE_COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")

OwnerId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_OWNER_PATTERN),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=_IDEMPOTENCY_PATTERN,
    ),
]
WorkerId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=_WORKER_PATTERN,
    ),
]
SafeTaskCode = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$",
    ),
]
Fingerprint = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
]
TaskKind = Literal["recent_review"]
TaskSchemaVersion = Literal["1.0"]


class TaskContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskPublicationStatus(StrEnum):
    PUBLISHED = "published"
    DEGRADED = "degraded"
    REJECTED = "rejected"


class TaskTerminal(TaskContractModel):
    terminal_reason: SafeTaskCode
    publication_status: TaskPublicationStatus
    report_available: bool

    @model_validator(mode="after")
    def validate_publication_projection(self) -> Self:
        if (
            self.publication_status is TaskPublicationStatus.REJECTED
            and self.report_available
        ):
            raise ValueError("rejected publication cannot expose a report")
        return self


class TaskCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"


class TaskRepositoryCreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    OWNER_CAPACITY_EXCEEDED = "owner_capacity_exceeded"
    GLOBAL_CAPACITY_EXCEEDED = "global_capacity_exceeded"


class CreateReviewTaskCommand(TaskContractModel):
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    request: RecentReviewProductRequest


class TaskCapacityPolicy(TaskContractModel):
    owner_active_limit: int = Field(default=3, ge=1, le=10_000)
    global_active_limit: int = Field(default=50, ge=1, le=100_000)

    @model_validator(mode="after")
    def validate_capacity_order(self) -> Self:
        if self.global_active_limit < self.owner_active_limit:
            raise ValueError(
                "global_active_limit must be greater than or equal to "
                "owner_active_limit"
            )
        return self


class PendingReviewTask(TaskContractModel):
    task_id: UUID
    run_id: str
    task_kind: TaskKind = "recent_review"
    schema_version: TaskSchemaVersion = "1.0"
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    request_fingerprint: Fingerprint
    request_payload: dict[str, JsonValue]
    created_at: datetime

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value)


class ReviewTask(TaskContractModel):
    task_id: UUID
    run_id: str
    task_kind: TaskKind
    schema_version: TaskSchemaVersion
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    request_fingerprint: Fingerprint
    request_payload: dict[str, JsonValue]

    status: TaskStatus
    worker_id: WorkerId | None
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None

    terminal_reason: SafeTaskCode | None
    publication_status: TaskPublicationStatus | None
    report_available: bool
    trace_reference: dict[str, JsonValue] | None
    receipt_reference: dict[str, JsonValue] | None
    artifact_reference: dict[str, JsonValue] | None

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("worker_id")
    @classmethod
    def validate_worker_id(cls, value: str | None) -> str | None:
        if value is not None and not _SAFE_COMPONENT_PATTERN.fullmatch(value):
            raise ValueError("worker_id must be a bounded safe identifier")
        return value

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str | None) -> str | None:
        if value is not None and not _SAFE_CODE_PATTERN.fullmatch(value):
            raise ValueError("terminal_reason must be a safe code")
        return value

    @field_validator("created_at", "updated_at", "claimed_at", "finished_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.claimed_at is not None and self.claimed_at < self.created_at:
            raise ValueError("claimed_at must not precede created_at")
        if self.finished_at is not None:
            if self.claimed_at is None or self.finished_at < self.claimed_at:
                raise ValueError("finished_at must not precede claimed_at")

        if self.status is TaskStatus.QUEUED:
            self._require_empty_execution_state("queued")
        elif self.status is TaskStatus.RUNNING:
            if self.worker_id is None or self.claimed_at is None:
                raise ValueError("running task requires worker_id and claimed_at")
            if any(
                value is not None
                for value in (
                    self.finished_at,
                    self.terminal_reason,
                    self.publication_status,
                )
            ) or self.report_available:
                raise ValueError("running task cannot contain terminal projection")
        else:
            if (
                self.worker_id is None
                or self.claimed_at is None
                or self.finished_at is None
                or self.terminal_reason is None
            ):
                raise ValueError("terminal task requires complete execution identity")
            if self.status is TaskStatus.SUCCEEDED:
                if self.publication_status is None:
                    raise ValueError("succeeded task requires publication_status")
                if (
                    self.publication_status is TaskPublicationStatus.REJECTED
                    and self.report_available
                ):
                    raise ValueError("rejected publication cannot expose a report")
            elif self.publication_status is not None or self.report_available:
                raise ValueError("failed task cannot contain publication projection")
        return self

    def _require_empty_execution_state(self, state: str) -> None:
        if any(
            value is not None
            for value in (
                self.worker_id,
                self.claimed_at,
                self.finished_at,
                self.terminal_reason,
                self.publication_status,
            )
        ) or self.report_available:
            raise ValueError(f"{state} task cannot contain execution state")


class ReviewTaskView(TaskContractModel):
    schema_version: TaskSchemaVersion
    task_id: UUID
    run_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None
    terminal_reason: str | None
    publication_status: TaskPublicationStatus | None
    report_available: bool

    @classmethod
    def from_task(cls, task: ReviewTask) -> "ReviewTaskView":
        if not isinstance(task, ReviewTask):
            raise TypeError("task must be a ReviewTask")
        return cls(
            schema_version=task.schema_version,
            task_id=task.task_id,
            run_id=task.run_id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            claimed_at=task.claimed_at,
            finished_at=task.finished_at,
            terminal_reason=task.terminal_reason,
            publication_status=task.publication_status,
            report_available=task.report_available,
        )


class TaskCreateResult(TaskContractModel):
    disposition: TaskCreateDisposition
    task: ReviewTaskView


class TaskRepositoryCreateResult(TaskContractModel):
    disposition: TaskRepositoryCreateDisposition
    task: ReviewTask | None = None

    @model_validator(mode="after")
    def validate_result_shape(self) -> Self:
        includes_task = self.disposition in {
            TaskRepositoryCreateDisposition.CREATED,
            TaskRepositoryCreateDisposition.REPLAYED,
        }
        if includes_task != (self.task is not None):
            raise ValueError("repository create result has an invalid task projection")
        return self


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("task timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "CreateReviewTaskCommand",
    "IdempotencyKey",
    "OwnerId",
    "PendingReviewTask",
    "ReviewTask",
    "ReviewTaskView",
    "SafeTaskCode",
    "TaskCapacityPolicy",
    "TaskCreateDisposition",
    "TaskCreateResult",
    "TaskPublicationStatus",
    "TaskRepositoryCreateDisposition",
    "TaskRepositoryCreateResult",
    "TaskStatus",
    "TaskTerminal",
    "WorkerId",
]
