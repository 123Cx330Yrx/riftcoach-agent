"""Public, body-free HTTP models for the asynchronous task API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.tasks.models import TaskCreateDisposition, TaskStatus
from app.tasks.reliable_runtime import (
    TaskCancelDisposition,
    TaskCancelResult,
    TaskEventPage,
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
)
from app.tasks.observability import TaskMetricsSnapshot, percentile


ApiVersion = Literal["2.0"]
ApiSchemaVersion = Literal["1.0"]
ApiErrorCode: TypeAlias = Literal[
    "request_invalid",
    "idempotency_conflict",
    "task_capacity_exceeded",
    "player_link_capacity_exceeded",
    "task_delete_conflict",
    "service_unavailable",
    "cleanup_pending",
    "task_not_found",
    "player_link_not_found",
    "player_profile_not_found",
    "run_not_found",
    "run_not_ready",
    "run_not_available",
    "report_not_available",
    "conversation_not_found",
    "run_integrity_failed",
    "evidence_not_available",
    "evidence_integrity_failed",
    "evidence_unavailable",
    "auth_unavailable",
    "authentication_required",
    "auth_session_invalid",
    "auth_session_expired",
    "auth_session_revoked",
    "csrf_invalid",
    "request_headers_too_large",
    "request_body_too_large",
    "rate_limited",
]
ReadinessCode: TypeAlias = Literal[
    "database_unavailable",
    "migration_not_current",
    "actor_context_unavailable",
    "service_configuration_invalid",
    "readiness_check_failed",
]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TaskLinks(ApiModel):
    task: str
    run: str
    report: str


class CreateReviewTaskResponse(ApiModel):
    schema_version: ApiSchemaVersion = "1.0"
    disposition: TaskCreateDisposition
    task_id: UUID
    run_id: str
    status: TaskStatus
    links: TaskLinks


class CreateConversationReviewTaskResponse(ApiModel):
    schema_version: Literal["2.0"] = "2.0"
    disposition: TaskCreateDisposition
    conversation_id: UUID
    task_id: UUID
    run_id: str
    status: TaskStatus
    links: TaskLinks


class DeleteTaskResponse(ApiModel):
    schema_version: ApiSchemaVersion = "1.0"
    task_id: UUID
    run_id: str | None = None
    status: Literal["hidden"] = "hidden"
    cleanup_pending: bool = False


class CancelTaskResponse(ApiModel):
    schema_version: ApiSchemaVersion = "1.0"
    task_id: UUID
    disposition: TaskCancelDisposition
    status: TaskStatus

    @classmethod
    def from_result(cls, result: TaskCancelResult) -> "CancelTaskResponse":
        if not isinstance(result, TaskCancelResult):
            raise TypeError("result must be a TaskCancelResult")
        return cls(
            task_id=result.task_id,
            disposition=result.disposition,
            status=result.status,
        )


class TaskEventResponse(ApiModel):
    event_schema_version: Literal["1.0"] = "1.0"
    event_cursor: int
    event_identity: str
    task_id: UUID
    run_id: str
    task_sequence: int
    event_kind: TaskLifecycleEventKind
    status_after: TaskStatus
    lease_generation: int
    reason: str | None = None
    occurred_at: datetime

    @classmethod
    def from_event(cls, event: TaskLifecycleEvent) -> "TaskEventResponse":
        if not isinstance(event, TaskLifecycleEvent):
            raise TypeError("event must be a TaskLifecycleEvent")
        return cls(
            event_cursor=event.event_cursor,
            event_identity=event.event_identity,
            task_id=event.task_id,
            run_id=event.run_id,
            task_sequence=event.task_sequence,
            event_kind=event.event_kind,
            status_after=event.status_after,
            lease_generation=event.lease_generation,
            reason=event.reason,
            occurred_at=event.occurred_at,
        )


class TaskEventPageResponse(ApiModel):
    schema_version: ApiSchemaVersion = "1.0"
    task_id: UUID
    after_cursor: int
    next_cursor: int
    limit: int
    has_more: bool
    events: tuple[TaskEventResponse, ...]

    @classmethod
    def from_page(
        cls,
        *,
        task_id: UUID,
        page: TaskEventPage,
    ) -> "TaskEventPageResponse":
        if not isinstance(page, TaskEventPage):
            raise TypeError("page must be a TaskEventPage")
        return cls(
            task_id=task_id,
            after_cursor=page.after_cursor,
            next_cursor=page.next_cursor,
            limit=page.limit,
            has_more=page.has_more,
            events=tuple(TaskEventResponse.from_event(item) for item in page.events),
        )


class ErrorResponse(ApiModel):
    code: ApiErrorCode
    run_id: str | None = None


class LivenessResponse(ApiModel):
    status: Literal["ok"] = "ok"
    api_version: ApiVersion = "2.0"
    schema_version: ApiSchemaVersion = "1.0"


class MetricsLatencyResponse(ApiModel):
    name: str
    sample_count: int
    p50_ms: float
    p95_ms: float


class MetricsResponse(ApiModel):
    schema_version: ApiSchemaVersion = "1.0"
    counters: dict[str, int]
    latencies: tuple[MetricsLatencyResponse, ...]

    @classmethod
    def from_snapshot(cls, snapshot: TaskMetricsSnapshot) -> "MetricsResponse":
        if not isinstance(snapshot, TaskMetricsSnapshot):
            raise TypeError("snapshot must be a TaskMetricsSnapshot")
        latency_rows = []
        for name in sorted(snapshot.latencies_ms):
            values = snapshot.latencies_ms[name]
            if not values:
                continue
            latency_rows.append(
                MetricsLatencyResponse(
                    name=name,
                    sample_count=len(values),
                    p50_ms=percentile(values, 0.50).value_ms,
                    p95_ms=percentile(values, 0.95).value_ms,
                )
            )
        return cls(
            counters=dict(sorted(snapshot.counters.items())),
            latencies=tuple(latency_rows),
        )


class ReadinessResult(ApiModel):
    is_ready: bool
    code: ReadinessCode | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.is_ready == (self.code is not None):
            raise ValueError("readiness result has an inconsistent code")
        return self

    @classmethod
    def ready(cls) -> "ReadinessResult":
        return cls(is_ready=True)

    @classmethod
    def not_ready(cls, code: ReadinessCode) -> "ReadinessResult":
        return cls(is_ready=False, code=code)


class ReadinessResponse(ApiModel):
    status: Literal["ready", "not_ready"]
    code: ReadinessCode | None = None
    api_version: ApiVersion = "2.0"
    schema_version: ApiSchemaVersion = "1.0"

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if (self.status == "ready") == (self.code is not None):
            raise ValueError("readiness response has an inconsistent code")
        return self

    @classmethod
    def from_result(cls, result: ReadinessResult) -> "ReadinessResponse":
        if not isinstance(result, ReadinessResult):
            raise TypeError("result must be a ReadinessResult")
        return cls(
            status="ready" if result.is_ready else "not_ready",
            code=result.code,
        )


__all__ = [
    "ApiErrorCode",
    "CancelTaskResponse",
    "CreateConversationReviewTaskResponse",
    "CreateReviewTaskResponse",
    "DeleteTaskResponse",
    "ErrorResponse",
    "LivenessResponse",
    "MetricsLatencyResponse",
    "MetricsResponse",
    "ReadinessCode",
    "ReadinessResponse",
    "ReadinessResult",
    "TaskLinks",
    "TaskEventPageResponse",
    "TaskEventResponse",
]
