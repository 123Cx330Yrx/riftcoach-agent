"""Thin FastAPI adapter for the durable asynchronous review-task API.

The adapter owns HTTP validation, trusted actor projection and safe status
mapping. It never constructs or runs Riot, Provider, Agent, Harness or Worker
components. POST only commits a queued task and returns ``202 Accepted``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import time
from typing import Protocol
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.types import Lifespan

from app.api.actor import (
    ActorContext,
    ActorContextProvider,
    ActorContextUnavailable,
)
from app.api.task_models import (
    ApiErrorCode,
    CreateReviewTaskResponse,
    DeleteTaskResponse,
    ErrorResponse,
    LivenessResponse,
    ReadinessResponse,
    ReadinessResult,
    TaskLinks,
)
from app.product.recent_review import RecentReviewProductRequest
from app.product.run_query import RunView
from app.tasks.models import (
    CreateReviewTaskCommand,
    ReviewTaskView,
    TaskCreateResult,
    TaskDeleteDisposition,
    TaskDeletionResult,
    TaskStatus,
)
from app.tasks.service import TaskServiceError
from app.tasks.deletion import TaskDeletionError
from app.tasks.observability import TaskObservability


class TaskServicePort(Protocol):
    def create(self, command: CreateReviewTaskCommand) -> TaskCreateResult: ...

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView: ...

    def get_task_by_run_id(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> ReviewTaskView: ...


class RunQueryPort(Protocol):
    def get_run(self, run_id: str) -> RunView: ...

    def get_report(self, run_id: str) -> str: ...


class ReadinessPort(Protocol):
    def check(self) -> ReadinessResult: ...


class TaskDeletionPort(Protocol):
    def delete(self, *, owner_id: str, task_id: UUID) -> TaskDeletionResult: ...


_CREATE_TASK_STATUS: Mapping[str, tuple[int, ApiErrorCode]] = {
    "idempotency_conflict": (409, "idempotency_conflict"),
    "owner_capacity_exceeded": (503, "task_capacity_exceeded"),
    "global_capacity_exceeded": (503, "task_capacity_exceeded"),
    "task_delete_conflict": (409, "task_delete_conflict"),
    "task_persistence_failed": (503, "service_unavailable"),
    "task_identity_invalid": (503, "service_unavailable"),
}
_IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"


def _error_response(
    code: ApiErrorCode,
    *,
    status_code: int,
    run_id: str | None = None,
) -> JSONResponse:
    body = ErrorResponse(code=code, run_id=run_id).model_dump(
        mode="json",
        exclude_none=True,
    )
    return JSONResponse(status_code=status_code, content=body)


def _task_lookup_error(
    error: TaskServiceError,
    *,
    not_found_code: ApiErrorCode,
) -> JSONResponse:
    if error.code == "task_not_found":
        return _error_response(not_found_code, status_code=404)
    return _error_response("service_unavailable", status_code=503)


def create_app(
    *,
    task_service: TaskServicePort,
    query_service: RunQueryPort,
    actor_provider: ActorContextProvider,
    readiness_probe: ReadinessPort,
    lifespan: Lifespan[FastAPI] | None = None,
    deletion_service: TaskDeletionPort | None = None,
    cors_origins: Sequence[str] = (),
    cors_allow_credentials: bool = False,
    observability: TaskObservability | None = None,
) -> FastAPI:
    """Create API V2 from explicit ports without doing deployment I/O."""

    for method_name in ("create", "get_task", "get_task_by_run_id"):
        if not callable(getattr(task_service, method_name, None)):
            raise TypeError(f"task_service must expose {method_name}()")
    for method_name in ("get_run", "get_report"):
        if not callable(getattr(query_service, method_name, None)):
            raise TypeError(f"query_service must expose {method_name}()")
    if not callable(actor_provider):
        raise TypeError("actor_provider must be callable")
    if not callable(getattr(readiness_probe, "check", None)):
        raise TypeError("readiness_probe must expose check()")
    if deletion_service is not None and not callable(
        getattr(deletion_service, "delete", None)
    ):
        raise TypeError("deletion_service must expose delete()")
    if observability is not None and not isinstance(
        observability,
        TaskObservability,
    ):
        raise TypeError("observability must be a TaskObservability")
    if not isinstance(cors_allow_credentials, bool):
        raise TypeError("cors_allow_credentials must be a bool")
    normalized_origins = tuple(cors_origins)
    if any(not isinstance(origin, str) or not origin.strip() for origin in normalized_origins):
        raise ValueError("cors_origins must contain non-blank strings")
    if "*" in normalized_origins and cors_allow_credentials:
        raise ValueError("wildcard CORS origins cannot use credentials")

    app = FastAPI(
        title="RiftCoach Agent API",
        version="2.0",
        description=(
            "Durable asynchronous task API for the recent-review product slice."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(normalized_origins),
        allow_credentials=cors_allow_credentials,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    def trusted_actor() -> ActorContext:
        context = actor_provider()
        if not isinstance(context, ActorContext):
            raise ActorContextUnavailable()
        return context

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # Details may contain Riot ID or other attacker-controlled text.
        del request, exc
        return _error_response("request_invalid", status_code=422)

    @app.exception_handler(ActorContextUnavailable)
    async def actor_unavailable_handler(
        request: Request,
        exc: ActorContextUnavailable,
    ) -> JSONResponse:
        del request, exc
        return _error_response("service_unavailable", status_code=503)

    @app.post(
        "/reviews/recent",
        status_code=202,
        response_model=CreateReviewTaskResponse,
        responses={
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def post_recent_review(
        product_request: RecentReviewProductRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
    ) -> CreateReviewTaskResponse | JSONResponse:
        started = time.perf_counter()
        try:
            command = CreateReviewTaskCommand(
                owner_id=actor.owner_id,
                idempotency_key=idempotency_key,
                request=product_request,
            )
            result = task_service.create(command)
            if not isinstance(result, TaskCreateResult):
                raise TypeError("task service returned an invalid result")
            task = result.task
            if observability is not None:
                observability.emit(
                    "api.task_created",
                    {
                        "task_id": str(task.task_id),
                        "run_id": task.run_id,
                        "status": 202,
                        "disposition": result.disposition.value,
                        "latency_ms": max(0.0, (time.perf_counter() - started) * 1000),
                    },
                )
            return CreateReviewTaskResponse(
                disposition=result.disposition,
                task_id=task.task_id,
                run_id=task.run_id,
                status=task.status,
                links=TaskLinks(
                    task=f"/tasks/{task.task_id}",
                    run=f"/runs/{task.run_id}",
                    report=f"/runs/{task.run_id}/report",
                ),
            )
        except TaskServiceError as error:
            status_code, code = _CREATE_TASK_STATUS.get(
                error.code,
                (503, "service_unavailable"),
            )
            response = _error_response(code, status_code=status_code)
            if observability is not None:
                observability.emit(
                    "api.task_create_rejected",
                    {
                        "status": status_code,
                        "reason": error.code,
                        "latency_ms": max(0.0, (time.perf_counter() - started) * 1000),
                    },
                )
            return response
        except ValidationError:
            return _error_response("request_invalid", status_code=422)
        except Exception:
            if observability is not None:
                observability.emit(
                    "api.task_create_failed",
                    {
                        "status": 503,
                        "reason": "service_unavailable",
                        "latency_ms": max(0.0, (time.perf_counter() - started) * 1000),
                    },
                )
            return _error_response("service_unavailable", status_code=503)

    @app.delete(
        "/tasks/{task_id}",
        response_model=DeleteTaskResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            202: {"model": DeleteTaskResponse},
            503: {"model": ErrorResponse},
        },
    )
    def delete_task(
        task_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> DeleteTaskResponse | JSONResponse:
        if deletion_service is None:
            return _error_response("service_unavailable", status_code=503)
        try:
            parsed_task_id = UUID(task_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("task_not_found", status_code=404)
        try:
            result = deletion_service.delete(
                owner_id=actor.owner_id,
                task_id=parsed_task_id,
            )
            if not isinstance(result, TaskDeletionResult):
                raise TypeError("deletion service returned an invalid result")
            if result.disposition is TaskDeleteDisposition.ACTIVE_CONFLICT:
                if observability is not None:
                    observability.emit(
                        "api.task_delete_rejected",
                        {
                            "task_id": str(result.task_id),
                            "run_id": result.run_id or "",
                            "status": 409,
                            "reason": "active_conflict",
                        },
                    )
                return _error_response(
                    "task_delete_conflict",
                    status_code=409,
                )
            status_code = (
                202
                if result.disposition is TaskDeleteDisposition.CLEANUP_PENDING
                else 200
            )
            response = DeleteTaskResponse(
                task_id=result.task_id,
                run_id=result.run_id,
                cleanup_pending=result.cleanup_pending,
            )
            if observability is not None:
                observability.emit(
                    "api.task_deleted",
                    {
                        "task_id": str(result.task_id),
                        "run_id": result.run_id or "",
                        "status": status_code,
                        "disposition": result.disposition.value,
                        "cleanup_pending": result.cleanup_pending,
                    },
                )
            if status_code == 202:
                return JSONResponse(
                    status_code=status_code,
                    content=response.model_dump(mode="json"),
                )
            return response
        except TaskDeletionError as error:
            if error.code == "task_not_found":
                return _error_response("task_not_found", status_code=404)
            if error.code == "task_delete_conflict":
                return _error_response("task_delete_conflict", status_code=409)
            return _error_response("service_unavailable", status_code=503)
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/tasks/{task_id}",
        response_model=ReviewTaskView,
        responses={
            404: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_task(
        task_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> ReviewTaskView | JSONResponse:
        try:
            parsed_task_id = UUID(task_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("task_not_found", status_code=404)
        try:
            result = task_service.get_task(
                owner_id=actor.owner_id,
                task_id=parsed_task_id,
            )
            if not isinstance(result, ReviewTaskView):
                raise TypeError("task service returned an invalid task view")
            return result
        except TaskServiceError as error:
            return _task_lookup_error(error, not_found_code="task_not_found")
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    def owned_run_task(
        actor: ActorContext,
        run_id: str,
    ) -> ReviewTaskView | JSONResponse:
        try:
            result = task_service.get_task_by_run_id(
                owner_id=actor.owner_id,
                run_id=run_id,
            )
            if not isinstance(result, ReviewTaskView) or result.run_id != run_id:
                raise TypeError("task service returned an invalid run identity")
            return result
        except TaskServiceError as error:
            return _task_lookup_error(error, not_found_code="run_not_found")
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/runs/{run_id}",
        response_model=RunView,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_run(
        run_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> RunView | JSONResponse:
        task = owned_run_task(actor, run_id)
        if isinstance(task, JSONResponse):
            return task
        if task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
            return _error_response(
                "run_not_ready",
                status_code=409,
                run_id=task.run_id,
            )
        if task.status is TaskStatus.FAILED:
            return _error_response(
                "run_not_available",
                status_code=409,
                run_id=task.run_id,
            )
        try:
            result = query_service.get_run(task.run_id)
            if not isinstance(result, RunView) or result.run_id != task.run_id:
                raise ValueError("run query returned an invalid identity")
            return result
        except Exception:
            return _error_response(
                "run_integrity_failed",
                status_code=500,
                run_id=task.run_id,
            )

    @app.get(
        "/runs/{run_id}/report",
        response_model=None,
        response_class=Response,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_report(
        run_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> Response:
        task = owned_run_task(actor, run_id)
        if isinstance(task, JSONResponse):
            return task
        if task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
            return _error_response(
                "run_not_ready",
                status_code=409,
                run_id=task.run_id,
            )
        if task.status is TaskStatus.FAILED or not task.report_available:
            return _error_response(
                "report_not_available",
                status_code=409,
                run_id=task.run_id,
            )
        try:
            report = query_service.get_report(task.run_id)
            if not isinstance(report, str) or not report.strip():
                raise ValueError("report query returned an invalid body")
            return Response(content=report, media_type="text/markdown")
        except Exception:
            return _error_response(
                "run_integrity_failed",
                status_code=500,
                run_id=task.run_id,
            )

    @app.get("/health/live", response_model=LivenessResponse)
    def liveness() -> LivenessResponse:
        return LivenessResponse()

    @app.get(
        "/health/ready",
        response_model=ReadinessResponse,
        response_model_exclude_none=True,
        responses={503: {"model": ReadinessResponse}},
    )
    def readiness() -> ReadinessResponse | JSONResponse:
        try:
            result = readiness_probe.check()
            if not isinstance(result, ReadinessResult):
                raise TypeError("readiness probe returned an invalid result")
        except Exception:
            result = ReadinessResult.not_ready("readiness_check_failed")
        response = ReadinessResponse.from_result(result)
        if result.is_ready:
            return response
        return JSONResponse(
            status_code=503,
            content=response.model_dump(mode="json", exclude_none=True),
        )

    return app


__all__ = [
    "ReadinessPort",
    "RunQueryPort",
    "TaskDeletionPort",
    "TaskServicePort",
    "create_app",
]
