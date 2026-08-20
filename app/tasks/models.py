from __future__ import annotations

import re
import unicodedata
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
from app.players.models import Puuid, RelationshipRole, RoutingRegion
from app.product.recent_review import (
    ConversationRecentReviewRequest,
    RecentReviewProductRequest,
)
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference


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
TaskSchemaVersion = Literal["1.0", "2.0"]


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
    run_id: str
    terminal_reason: SafeTaskCode
    publication_status: TaskPublicationStatus
    report_available: bool
    trace_reference: RuntimeTraceReference
    receipt_reference: RunReceiptReference
    artifact_reference: RuntimeArtifactReference | None = None

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @model_validator(mode="after")
    def validate_publication_projection(self) -> Self:
        if self.trace_reference.run_id != self.run_id:
            raise ValueError("trace_reference run_id must match terminal run_id")
        if self.receipt_reference.run_id != self.run_id:
            raise ValueError("receipt_reference run_id must match terminal run_id")
        if self.publication_status is TaskPublicationStatus.REJECTED:
            if self.report_available or self.artifact_reference is not None:
                raise ValueError("rejected publication cannot expose a report")
        elif not self.report_available or self.artifact_reference is None:
            raise ValueError(
                "published or degraded terminal requires final report evidence"
            )
        if (
            self.artifact_reference is not None
            and self.artifact_reference.kind != "final_report"
        ):
            raise ValueError("artifact_reference must identify the final report")
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
    CONVERSATION_UNAVAILABLE = "conversation_unavailable"


class TaskRepositoryDeleteDisposition(StrEnum):
    """Database-side result before any file cleanup is attempted."""

    DELETED = "deleted"
    ACTIVE_CONFLICT = "active_conflict"
    NOT_FOUND = "not_found"


class TaskRepositoryDeleteResult(TaskContractModel):
    disposition: TaskRepositoryDeleteDisposition
    run_id: str | None = None

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str | None) -> str | None:
        return None if value is None else normalize_run_id(value)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.disposition is TaskRepositoryDeleteDisposition.NOT_FOUND:
            if self.run_id is not None:
                raise ValueError("not-found deletion cannot expose a run_id")
        elif self.run_id is None:
            raise ValueError("known deletion result requires a run_id")
        return self


class TaskDeleteDisposition(StrEnum):
    """Safe product projection after SQL hiding and file cleanup attempt."""

    DELETED = "deleted"
    ALREADY_HIDDEN = "already_hidden"
    CLEANUP_PENDING = "cleanup_pending"
    ACTIVE_CONFLICT = "active_conflict"


class TaskDeletionResult(TaskContractModel):
    disposition: TaskDeleteDisposition
    task_id: UUID
    run_id: str | None = None

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str | None) -> str | None:
        return None if value is None else normalize_run_id(value)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.disposition is TaskDeleteDisposition.ALREADY_HIDDEN:
            if self.run_id is not None:
                raise ValueError("already-hidden deletion cannot expose a run_id")
        elif self.run_id is None:
            raise ValueError("known deletion result requires a run_id")
        return self

    @property
    def cleanup_pending(self) -> bool:
        return self.disposition is TaskDeleteDisposition.CLEANUP_PENDING


class CreateReviewTaskCommand(TaskContractModel):
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    request: RecentReviewProductRequest


class ConversationReviewTaskBinding(TaskContractModel):
    conversation_id: UUID
    relationship_id: UUID
    player_subject_id: UUID
    relationship_role: RelationshipRole


class ConversationReviewExecutionTarget(TaskContractModel):
    """Private trusted lookup data; never part of the public Task view."""

    puuid: Puuid
    routing_region: RoutingRegion
    game_name: str = Field(min_length=1, max_length=64)
    tag_line: str = Field(min_length=1, max_length=32)

    @field_validator("game_name", "tag_line")
    @classmethod
    def validate_display_component(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.strip())
        if not normalized or any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError("display identity must be bounded visible text")
        return normalized


class CreateConversationReviewTaskCommand(TaskContractModel):
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    conversation_id: UUID
    request: ConversationRecentReviewRequest


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


class PendingConversationReviewTask(TaskContractModel):
    task_id: UUID
    run_id: str
    task_kind: TaskKind = "recent_review"
    schema_version: Literal["2.0"] = "2.0"
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    conversation_id: UUID
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
    conversation_binding: ConversationReviewTaskBinding | None = None
    execution_target: ConversationReviewExecutionTarget | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    status: TaskStatus
    worker_id: WorkerId | None
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None

    terminal_reason: SafeTaskCode | None
    publication_status: TaskPublicationStatus | None
    report_available: bool
    trace_reference: RuntimeTraceReference | None
    receipt_reference: RunReceiptReference | None
    artifact_reference: RuntimeArtifactReference | None

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
        if self.schema_version == "1.0":
            if (
                self.conversation_binding is not None
                or self.execution_target is not None
            ):
                raise ValueError("schema 1.0 task cannot contain conversation identity")
        elif (
            self.conversation_binding is None
            or self.execution_target is None
        ):
            raise ValueError(
                "schema 2.0 task requires binding and private execution target"
            )

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
            ) or self.report_available or any(
                value is not None
                for value in (
                    self.trace_reference,
                    self.receipt_reference,
                    self.artifact_reference,
                )
            ):
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
                TaskTerminal(
                    run_id=self.run_id,
                    terminal_reason=self.terminal_reason,
                    publication_status=self.publication_status,
                    report_available=self.report_available,
                    trace_reference=self.trace_reference,
                    receipt_reference=self.receipt_reference,
                    artifact_reference=self.artifact_reference,
                )
            elif (
                self.publication_status is not None
                or self.report_available
                or any(
                    value is not None
                    for value in (
                        self.trace_reference,
                        self.receipt_reference,
                        self.artifact_reference,
                    )
                )
            ):
                raise ValueError(
                    "failed task cannot contain publication or evidence projection"
                )
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
        ) or self.report_available or any(
            value is not None
            for value in (
                self.trace_reference,
                self.receipt_reference,
                self.artifact_reference,
            )
        ):
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
    "ConversationReviewExecutionTarget",
    "ConversationReviewTaskBinding",
    "CreateConversationReviewTaskCommand",
    "CreateReviewTaskCommand",
    "IdempotencyKey",
    "OwnerId",
    "PendingReviewTask",
    "PendingConversationReviewTask",
    "ReviewTask",
    "ReviewTaskView",
    "SafeTaskCode",
    "TaskCapacityPolicy",
    "TaskCreateDisposition",
    "TaskCreateResult",
    "TaskDeleteDisposition",
    "TaskDeletionResult",
    "TaskPublicationStatus",
    "TaskRepositoryDeleteDisposition",
    "TaskRepositoryDeleteResult",
    "TaskRepositoryCreateDisposition",
    "TaskRepositoryCreateResult",
    "TaskStatus",
    "TaskTerminal",
    "WorkerId",
]
