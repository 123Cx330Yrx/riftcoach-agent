"""Public, body-free HTTP models for the asynchronous task API."""

from __future__ import annotations

from typing import Literal, Self, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.tasks.models import TaskCreateDisposition, TaskStatus


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
    "run_not_found",
    "run_not_ready",
    "run_not_available",
    "report_not_available",
    "run_integrity_failed",
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


class DeleteTaskResponse(ApiModel):
    schema_version: ApiSchemaVersion = "1.0"
    task_id: UUID
    run_id: str | None = None
    status: Literal["hidden"] = "hidden"
    cleanup_pending: bool = False


class ErrorResponse(ApiModel):
    code: ApiErrorCode
    run_id: str | None = None


class LivenessResponse(ApiModel):
    status: Literal["ok"] = "ok"
    api_version: ApiVersion = "2.0"
    schema_version: ApiSchemaVersion = "1.0"


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
    "CreateReviewTaskResponse",
    "DeleteTaskResponse",
    "ErrorResponse",
    "LivenessResponse",
    "ReadinessCode",
    "ReadinessResponse",
    "ReadinessResult",
    "TaskLinks",
]
