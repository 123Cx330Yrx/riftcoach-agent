"""Thin FastAPI adapter for durable review, player-link and conversation APIs.

The adapter owns HTTP validation, trusted actor projection and safe status
mapping. It never constructs or runs Riot, Provider, Agent, Harness or Worker
components. Review/player-link POST routes only persist queued intent and return
``202 Accepted``; Conversation POST routes perform bounded synchronous
PostgreSQL control-plane mutations without external I/O.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.types import Lifespan

from app.auth.session import (
    AuthSessionError,
    AuthSessionService,
    CookiePolicy,
)
from app.api.actor import (
    ActorContext,
    ActorContextProvider,
    ActorContextUnavailable,
)
from app.api.auth_models import AuthSessionResponse
from app.api.security import (
    InMemoryRateLimiter,
    RequestBudget,
    RequestBudgetMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.conversation_models import (
    AppendUserMessageRequest,
    ConversationApiErrorCode,
    ConversationErrorResponse,
    ConversationMessagePageResponse,
    ConversationMessageResponse,
    ConversationResponse,
    CreateConversationRequest,
    CreateConversationResponse,
)
from app.api.player_models import (
    CreatePlayerLinkRequest,
    CreatePlayerLinkResponse,
    PlayerLinkResponse,
    PlayerProfilePageResponse,
)
from app.api.live_workbench_models import (
    LatestProfileReviewResponse,
    RecentSummaryResponse,
)
from app.api.memory_models import (
    CreateMemoryCandidateRequest,
    MemoryCandidateApiErrorCode,
    MemoryCandidateErrorResponse,
    MemoryCandidateResponse,
)
from app.api.task_models import (
    ApiErrorCode,
    CancelTaskResponse,
    CreateConversationReviewTaskResponse,
    CreateReviewTaskResponse,
    DeleteTaskResponse,
    ErrorResponse,
    LivenessResponse,
    ReadinessResponse,
    ReadinessResult,
    TaskLinks,
    TaskEventPageResponse,
)
from app.api.typed_memory_models import (
    TypedMemoryApiErrorCode,
    TypedMemoryErrorResponse,
    TypedMemoryPageResponse,
)
from app.api.training_models import (
    TrainingApiErrorCode,
    TrainingErrorResponse,
    TrainingPlanPageResponse,
    TrainingProgressPageResponse,
)
from app.api.lifecycle_models import (
    LifecycleApiErrorCode,
    LifecycleErrorResponse,
    OwnerDataDeleteRequest,
    OwnerDataDeletionResponse,
    OwnerDataExportResponse,
)
from app.api.evidence_models import EvidenceSnapshotResponse, ProductStateResponse
from app.conversations.models import (
    AppendUserMessageCommand,
    ConversationCreateResult,
    ConversationMessagePage,
    ConversationMessageView,
    ConversationView,
    CreateConversationCommand,
)
from app.conversations.ports import ConversationServicePort
from app.conversations.service import ConversationServiceError
from app.memory.models import (
    CandidateKind,
    CreateMemoryCandidateCommand,
    MemoryCandidateView,
    MemoryOperation,
    ProvenanceKind,
    TargetScope,
)
from app.memory.ports import MemoryCandidateServicePort
from app.memory.service import MemoryCandidateServiceError
from app.memory.typed_models import TypedMemoryPage
from app.memory.typed_ports import TypedMemoryQueryServicePort
from app.memory.typed_service import TypedMemoryQueryServiceError
from app.memory.training_models import TrainingPlanPage, TrainingProgressPage
from app.memory.training_query_ports import TrainingQueryServicePort
from app.memory.training_service import TrainingQueryServiceError
from app.lifecycle.models import (
    OwnerDataDeleteCommand,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerDataExport,
)
from app.lifecycle.service import OwnerDataLifecycleError
from app.players.models import (
    CreatePlayerLinkCommand,
    PlayerLinkCreateResult,
    PlayerLinkTaskView,
    PlayerProfilePage,
    RelationshipRole,
    RoutingRegion,
)
from app.players.service import PlayerLinkServiceError
from app.product.recent_review import (
    ConversationRecentReviewRequest,
    RecentReviewProductRequest,
)
from app.product.latest_review import (
    LatestProfileReviewResult,
    LatestProfileReviewServiceError,
)
from app.product.run_query import RecentSummaryView, RunQueryError, RunView
from app.tasks.models import (
    CreateConversationReviewTaskCommand,
    CreateReviewTaskCommand,
    ReviewTaskView,
    TaskCreateResult,
    TaskDeleteDisposition,
    TaskDeletionResult,
    TaskStatus,
)
from app.tasks.service import TaskServiceError
from app.tasks.reliable_runtime import TaskCancelResult, TaskEventPage
from app.tasks.deletion import TaskDeletionError
from app.tasks.observability import TaskObservability
from app.tasks.sse import (
    TaskEventStreamServiceError,
    resolve_event_cursor,
)
from app.evidence.service import EvidenceProductServiceError
from app.evidence.storage import EvidenceSnapshotView, ProductRunState


class TaskServicePort(Protocol):
    def create(self, command: CreateReviewTaskCommand) -> TaskCreateResult: ...

    def create_conversation_review(
        self,
        command: CreateConversationReviewTaskCommand,
    ) -> TaskCreateResult: ...

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView: ...

    def get_task_by_run_id(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> ReviewTaskView: ...

    def request_cancel(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        request_id: str,
    ) -> TaskCancelResult: ...

    def read_events(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int = 0,
        limit: int = 50,
    ) -> TaskEventPage: ...


class PlayerLinkServicePort(Protocol):
    def create(self, command: CreatePlayerLinkCommand) -> PlayerLinkCreateResult: ...

    def get_link(
        self,
        *,
        owner_id: str,
        link_task_id: UUID,
    ) -> PlayerLinkTaskView: ...

    def list_profiles(
        self,
        *,
        owner_id: str,
        limit: int = 50,
    ) -> PlayerProfilePage: ...


class RunQueryPort(Protocol):
    def get_run(self, run_id: str) -> RunView: ...

    def get_report(self, run_id: str) -> str: ...

    def get_recent_summary(self, run_id: str) -> RecentSummaryView: ...


class LatestProfileReviewServicePort(Protocol):
    def get_latest(
        self,
        *,
        owner_id: str,
        player_profile_id: UUID,
    ) -> LatestProfileReviewResult: ...


class EvidenceProductServicePort(Protocol):
    def get_evidence(self, *, owner_id: str, run_id: str) -> EvidenceSnapshotView: ...

    def get_product_state(self, *, owner_id: str, run_id: str) -> ProductRunState: ...


class TaskEventStreamServicePort(Protocol):
    def preflight(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView: ...

    def stream(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int,
    ): ...


class ReadinessPort(Protocol):
    def check(self) -> ReadinessResult: ...


class TaskDeletionPort(Protocol):
    def delete(self, *, owner_id: str, task_id: UUID) -> TaskDeletionResult: ...


class OwnerDataLifecyclePort(Protocol):
    def export(self, *, owner_id: str) -> OwnerDataExport: ...

    def delete(self, command: OwnerDataDeleteCommand) -> OwnerDataDeletionMarker: ...

    def retry(self, *, owner_id: str, marker_id: UUID) -> OwnerDataDeletionMarker: ...


_CREATE_TASK_STATUS: Mapping[str, tuple[int, ApiErrorCode]] = {
    "idempotency_conflict": (409, "idempotency_conflict"),
    "owner_capacity_exceeded": (503, "task_capacity_exceeded"),
    "global_capacity_exceeded": (503, "task_capacity_exceeded"),
    "task_delete_conflict": (409, "task_delete_conflict"),
    "task_persistence_failed": (503, "service_unavailable"),
    "task_identity_invalid": (503, "service_unavailable"),
}
_CREATE_PLAYER_LINK_STATUS: Mapping[str, tuple[int, ApiErrorCode]] = {
    "idempotency_conflict": (409, "idempotency_conflict"),
    "owner_capacity_exceeded": (503, "player_link_capacity_exceeded"),
    "global_capacity_exceeded": (503, "player_link_capacity_exceeded"),
    "link_persistence_failed": (503, "service_unavailable"),
    "link_identity_invalid": (503, "service_unavailable"),
}
_CONVERSATION_ERROR_STATUS: Mapping[
    str,
    tuple[int, ConversationApiErrorCode],
] = {
    "request_invalid": (422, "request_invalid"),
    "conversation_not_found": (404, "conversation_not_found"),
    "conversation_idempotency_conflict": (
        409,
        "conversation_idempotency_conflict",
    ),
    "conversation_archived": (409, "conversation_archived"),
    "service_unavailable": (503, "service_unavailable"),
}
_MEMORY_CANDIDATE_ERROR_STATUS: Mapping[
    str,
    tuple[int, MemoryCandidateApiErrorCode],
] = {
    "request_invalid": (422, "request_invalid"),
    "conversation_not_found": (404, "conversation_not_found"),
    "candidate_not_found": (404, "candidate_not_found"),
    "candidate_idempotency_conflict": (409, "candidate_idempotency_conflict"),
    "candidate_gate_rejected": (422, "candidate_gate_rejected"),
    "candidate_terminal_conflict": (409, "candidate_terminal_conflict"),
    "candidate_expired": (409, "candidate_expired"),
    "memory_target_unavailable": (409, "memory_target_unavailable"),
    "memory_payload_invalid": (422, "memory_payload_invalid"),
    "memory_version_conflict": (409, "memory_version_conflict"),
    "service_unavailable": (503, "service_unavailable"),
}
_TYPED_MEMORY_ERROR_STATUS: Mapping[
    str,
    tuple[int, TypedMemoryApiErrorCode],
] = {
    "memory_scope_not_found": (404, "memory_scope_not_found"),
    "service_unavailable": (503, "service_unavailable"),
}
_TRAINING_ERROR_STATUS: Mapping[str, tuple[int, TrainingApiErrorCode]] = {
    "training_scope_not_found": (404, "training_scope_not_found"),
    "training_plan_not_found": (404, "training_plan_not_found"),
    "service_unavailable": (503, "service_unavailable"),
}
_LIFECYCLE_ERROR_STATUS: Mapping[str, tuple[int, LifecycleApiErrorCode]] = {
    "deletion_not_found": (404, "deletion_not_found"),
    "idempotency_conflict": (409, "idempotency_conflict"),
    "export_too_large": (409, "export_too_large"),
    "lifecycle_unavailable": (503, "lifecycle_unavailable"),
    "lifecycle_integrity_failed": (503, "lifecycle_integrity_failed"),
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


def _evidence_product_error(
    error: EvidenceProductServiceError,
    *,
    run_id: str,
) -> JSONResponse:
    mapping: Mapping[str, tuple[int, ApiErrorCode]] = {
        "run_not_found": (404, "run_not_found"),
        "evidence_not_available": (409, "evidence_not_available"),
        "evidence_integrity_failed": (500, "evidence_integrity_failed"),
        "evidence_unavailable": (503, "evidence_unavailable"),
    }
    status_code, code = mapping.get(
        error.code,
        (503, "evidence_unavailable"),
    )
    return _error_response(code, status_code=status_code, run_id=run_id)


def _conversation_error_response(
    code: ConversationApiErrorCode,
    *,
    status_code: int,
) -> JSONResponse:
    body = ConversationErrorResponse(code=code).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


def _conversation_service_error(
    error: ConversationServiceError,
) -> JSONResponse:
    status_code, code = _CONVERSATION_ERROR_STATUS.get(
        error.code,
        (503, "service_unavailable"),
    )
    return _conversation_error_response(code, status_code=status_code)


def _parse_conversation_id(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError):
        return None


def _memory_candidate_error_response(
    code: MemoryCandidateApiErrorCode,
    *,
    status_code: int,
    reason: str | None = None,
) -> JSONResponse:
    body = MemoryCandidateErrorResponse(code=code, reason=reason).model_dump(
        mode="json",
        exclude_none=True,
    )
    return JSONResponse(status_code=status_code, content=body)


def _memory_candidate_service_error(error: MemoryCandidateServiceError) -> JSONResponse:
    status_code, code = _MEMORY_CANDIDATE_ERROR_STATUS.get(
        error.code,
        (503, "service_unavailable"),
    )
    reason = error.reason_code if code == "candidate_gate_rejected" else None
    return _memory_candidate_error_response(code, status_code=status_code, reason=reason)


def _parse_candidate_id(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError):
        return None


def _typed_memory_error_response(
    code: TypedMemoryApiErrorCode,
    *,
    status_code: int,
) -> JSONResponse:
    body = TypedMemoryErrorResponse(code=code).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


def _typed_memory_service_error(error: TypedMemoryQueryServiceError) -> JSONResponse:
    status_code, code = _TYPED_MEMORY_ERROR_STATUS.get(
        error.code,
        (503, "service_unavailable"),
    )
    return _typed_memory_error_response(code, status_code=status_code)


def _training_error_response(code: TrainingApiErrorCode, *, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=TrainingErrorResponse(code=code).model_dump(mode="json"),
    )


def _training_service_error(error: TrainingQueryServiceError) -> JSONResponse:
    status_code, code = _TRAINING_ERROR_STATUS.get(
        error.code,
        (503, "service_unavailable"),
    )
    return _training_error_response(code, status_code=status_code)


def _lifecycle_error_response(
    code: LifecycleApiErrorCode,
    *,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=LifecycleErrorResponse(code=code).model_dump(mode="json"),
    )


def _lifecycle_service_error(error: OwnerDataLifecycleError) -> JSONResponse:
    status_code, code = _LIFECYCLE_ERROR_STATUS.get(
        error.code,
        (503, "lifecycle_unavailable"),
    )
    return _lifecycle_error_response(code, status_code=status_code)


class _AuthBoundaryError(RuntimeError):
    def __init__(self, *, code: ApiErrorCode, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _auth_error_response(*, code: ApiErrorCode, status_code: int) -> JSONResponse:
    return _error_response(code, status_code=status_code)


def _auth_session_error_code(error: AuthSessionError) -> tuple[ApiErrorCode, int]:
    mapping: Mapping[str, tuple[ApiErrorCode, int]] = {
        "session_invalid": ("auth_session_invalid", 401),
        "session_expired": ("auth_session_expired", 401),
        "session_revoked": ("auth_session_revoked", 401),
    }
    return mapping.get(error.args[0] if error.args else "", ("auth_session_invalid", 401))


def create_app(
    *,
    task_service: TaskServicePort,
    player_link_service: PlayerLinkServicePort,
    query_service: RunQueryPort,
    actor_provider: ActorContextProvider,
    readiness_probe: ReadinessPort,
    lifespan: Lifespan[FastAPI] | None = None,
    deletion_service: TaskDeletionPort | None = None,
    cors_origins: Sequence[str] = (),
    cors_allow_credentials: bool = False,
    observability: TaskObservability | None = None,
    conversation_service: ConversationServicePort | None = None,
    memory_candidate_service: MemoryCandidateServicePort | None = None,
    typed_memory_query_service: TypedMemoryQueryServicePort | None = None,
    training_query_service: TrainingQueryServicePort | None = None,
    owner_data_lifecycle_service: OwnerDataLifecyclePort | None = None,
    evidence_product_service: EvidenceProductServicePort | None = None,
    task_event_stream_service: TaskEventStreamServicePort | None = None,
    latest_profile_review_service: LatestProfileReviewServicePort | None = None,
    auth_session_service: AuthSessionService | None = None,
    auth_cookie_policy: CookiePolicy | None = None,
    request_budget: RequestBudget | None = None,
    rate_limiter: InMemoryRateLimiter | None = None,
) -> FastAPI:
    """Create API V2 from explicit ports without doing deployment I/O."""

    for method_name in ("create", "get_task", "get_task_by_run_id"):
        if not callable(getattr(task_service, method_name, None)):
            raise TypeError(f"task_service must expose {method_name}()")
    for method_name in ("create", "get_link"):
        if not callable(getattr(player_link_service, method_name, None)):
            raise TypeError(f"player_link_service must expose {method_name}()")
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
    if conversation_service is not None:
        for method_name in (
            "create",
            "get_conversation",
            "append_user_message",
            "list_messages",
            "archive_conversation",
            "hide_conversation",
        ):
            if not callable(getattr(conversation_service, method_name, None)):
                raise TypeError(
                    f"conversation_service must expose {method_name}()"
                )
    if memory_candidate_service is not None:
        for method_name in ("create", "get", "accept", "reject"):
            if not callable(getattr(memory_candidate_service, method_name, None)):
                raise TypeError(
                    f"memory_candidate_service must expose {method_name}()"
                )
    if typed_memory_query_service is not None:
        for method_name in ("preferences", "profile", "reviews"):
            if not callable(getattr(typed_memory_query_service, method_name, None)):
                raise TypeError(
                    f"typed_memory_query_service must expose {method_name}()"
                )
    if training_query_service is not None:
        for method_name in ("plans", "progress"):
            if not callable(getattr(training_query_service, method_name, None)):
                raise TypeError(
                    f"training_query_service must expose {method_name}()"
                )
    if owner_data_lifecycle_service is not None:
        for method_name in ("export", "delete", "retry"):
            if not callable(getattr(owner_data_lifecycle_service, method_name, None)):
                raise TypeError(
                    f"owner_data_lifecycle_service must expose {method_name}()"
                )
    if evidence_product_service is not None:
        for method_name in ("get_evidence", "get_product_state"):
            if not callable(getattr(evidence_product_service, method_name, None)):
                raise TypeError(
                    f"evidence_product_service must expose {method_name}()"
                )
    if task_event_stream_service is not None:
        for method_name in ("preflight", "stream"):
            if not callable(getattr(task_event_stream_service, method_name, None)):
                raise TypeError(
                    f"task_event_stream_service must expose {method_name}()"
                )
    if latest_profile_review_service is not None and not callable(
        getattr(latest_profile_review_service, "get_latest", None)
    ):
        raise TypeError(
            "latest_profile_review_service must expose get_latest()"
        )
    if auth_session_service is not None:
        for method_name in ("issue", "resolve", "verify_csrf", "revoke"):
            if not callable(getattr(auth_session_service, method_name, None)):
                raise TypeError(
                    f"auth_session_service must expose {method_name}()"
                )
    selected_cookie_policy = auth_cookie_policy or CookiePolicy()
    if not isinstance(selected_cookie_policy, CookiePolicy):
        raise TypeError("auth_cookie_policy must be a CookiePolicy")
    if request_budget is not None and not isinstance(request_budget, RequestBudget):
        raise TypeError("request_budget must be a RequestBudget")
    if rate_limiter is not None and not isinstance(rate_limiter, InMemoryRateLimiter):
        raise TypeError("rate_limiter must be an InMemoryRateLimiter")
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
            "Durable API for recent reviews, Riot player links and "
            "owner-scoped conversations and Memory Candidates."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(normalized_origins),
        allow_credentials=cors_allow_credentials,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key", "Last-Event-ID"],
    )
    app.add_middleware(SecurityHeadersMiddleware, include_hsts=False)
    if request_budget is not None:
        app.add_middleware(
            RequestBudgetMiddleware,
            budget=request_budget,
            rate_limiter=rate_limiter,
        )

    @app.middleware("http")
    async def session_csrf_boundary(request: Request, call_next):
        if (
            auth_session_service is not None
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and not (
                request.method == "POST"
                and request.url.path == "/auth/session"
            )
        ):
            cookie_value = request.cookies.get(selected_cookie_policy.name)
            if cookie_value is None:
                return _auth_error_response(
                    code="authentication_required",
                    status_code=401,
                )
            csrf_token = request.headers.get("X-CSRF-Token")
            if csrf_token is None:
                return _auth_error_response(code="csrf_invalid", status_code=403)
            try:
                csrf_valid = auth_session_service.verify_csrf(
                    cookie_value=cookie_value,
                    csrf_token=csrf_token,
                    now=datetime.now(timezone.utc),
                )
            except AuthSessionError as error:
                code, status_code = _auth_session_error_code(error)
                return _auth_error_response(code=code, status_code=status_code)
            if not csrf_valid:
                return _auth_error_response(code="csrf_invalid", status_code=403)
        return await call_next(request)

    def trusted_actor(request: Request) -> ActorContext:
        if auth_session_service is not None:
            cookie_value = request.cookies.get(selected_cookie_policy.name)
            if cookie_value is None:
                raise _AuthBoundaryError(
                    code="authentication_required",
                    status_code=401,
                )
            try:
                context = auth_session_service.resolve(
                    cookie_value=cookie_value,
                    now=datetime.now(timezone.utc),
                )
            except AuthSessionError as error:
                code, status_code = _auth_session_error_code(error)
                raise _AuthBoundaryError(
                    code=code,
                    status_code=status_code,
                ) from error
            if not isinstance(context, ActorContext):
                raise _AuthBoundaryError(
                    code="auth_session_invalid",
                    status_code=401,
                )
            return context
        context = actor_provider()
        if not isinstance(context, ActorContext):
            raise ActorContextUnavailable()
        return context

    async def require_empty_body(request: Request) -> None:
        if await request.body():
            # Archive/hide have no public command fields.  Rejecting a body
            # prevents clients from believing owner, subject or role input
            # influenced the lifecycle operation.
            raise RequestValidationError([])

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

    @app.exception_handler(_AuthBoundaryError)
    async def auth_boundary_handler(
        request: Request,
        exc: _AuthBoundaryError,
    ) -> JSONResponse:
        del request
        return _auth_error_response(code=exc.code, status_code=exc.status_code)

    @app.post(
        "/auth/session",
        response_model=AuthSessionResponse,
        responses={503: {"model": ErrorResponse}},
    )
    def issue_auth_session(response: Response) -> AuthSessionResponse | JSONResponse:
        if auth_session_service is None:
            return _auth_error_response(code="auth_unavailable", status_code=503)
        try:
            issued = auth_session_service.issue()
        except Exception:
            return _auth_error_response(code="auth_unavailable", status_code=503)
        response.set_cookie(
            key=selected_cookie_policy.name,
            value=issued.cookie_value,
            expires=issued.expires_at,
            secure=selected_cookie_policy.secure,
            httponly=selected_cookie_policy.http_only,
            samesite=selected_cookie_policy.same_site,
            path=selected_cookie_policy.path,
        )
        return AuthSessionResponse(
            csrf_token=issued.csrf_token,
            expires_at=issued.expires_at,
        )

    @app.delete(
        "/auth/session",
        status_code=204,
        response_model=None,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def revoke_auth_session(request: Request, response: Response) -> Response:
        if auth_session_service is None:
            return _auth_error_response(code="auth_unavailable", status_code=503)
        cookie_value = request.cookies.get(selected_cookie_policy.name)
        if cookie_value is None:
            return _auth_error_response(
                code="authentication_required",
                status_code=401,
            )
        try:
            auth_session_service.revoke(
                cookie_value=cookie_value,
                now=datetime.now(timezone.utc),
            )
        except AuthSessionError as error:
            code, status_code = _auth_session_error_code(error)
            return _auth_error_response(code=code, status_code=status_code)
        response.delete_cookie(
            key=selected_cookie_policy.name,
            path=selected_cookie_policy.path,
            secure=selected_cookie_policy.secure,
            httponly=selected_cookie_policy.http_only,
            samesite=selected_cookie_policy.same_site,
        )
        response.status_code = 204
        return response

    @app.post(
        "/conversations",
        status_code=201,
        response_model=CreateConversationResponse,
        responses={
            200: {"model": CreateConversationResponse},
            404: {"model": ConversationErrorResponse},
            409: {"model": ConversationErrorResponse},
            422: {"model": ConversationErrorResponse},
            503: {"model": ConversationErrorResponse},
        },
    )
    def post_conversation(
        conversation_request: CreateConversationRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
    ) -> CreateConversationResponse | JSONResponse:
        if conversation_service is None:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )
        try:
            command = CreateConversationCommand(
                owner_id=actor.owner_id,
                idempotency_key=idempotency_key,
                relationship_id=conversation_request.player_profile_id,
            )
        except ValidationError:
            return _conversation_error_response(
                "request_invalid",
                status_code=422,
            )
        try:
            result = conversation_service.create(command)
            if not isinstance(result, ConversationCreateResult):
                raise TypeError("conversation service returned an invalid result")
            if result.conversation.relationship_id != command.relationship_id:
                raise TypeError("conversation service returned a mismatched relationship")
            response = CreateConversationResponse.from_result(result)
            if result.disposition.value == "replayed":
                return JSONResponse(
                    status_code=200,
                    content=response.model_dump(mode="json"),
                )
            return response
        except ConversationServiceError as error:
            return _conversation_service_error(error)
        except Exception:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )

    @app.get(
        "/conversations/{conversation_id}",
        response_model=ConversationResponse,
        responses={
            404: {"model": ConversationErrorResponse},
            503: {"model": ConversationErrorResponse},
        },
    )
    def get_conversation(
        conversation_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> ConversationResponse | JSONResponse:
        parsed_conversation_id = _parse_conversation_id(conversation_id)
        if parsed_conversation_id is None:
            return _conversation_error_response(
                "conversation_not_found",
                status_code=404,
            )
        if conversation_service is None:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )
        try:
            view = conversation_service.get_conversation(
                owner_id=actor.owner_id,
                conversation_id=parsed_conversation_id,
            )
            if (
                not isinstance(view, ConversationView)
                or view.conversation_id != parsed_conversation_id
            ):
                raise TypeError("conversation service returned an invalid view")
            return ConversationResponse.from_view(view)
        except ConversationServiceError as error:
            return _conversation_service_error(error)
        except Exception:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )

    @app.post(
        "/conversations/{conversation_id}/messages",
        status_code=201,
        response_model=ConversationMessageResponse,
        responses={
            404: {"model": ConversationErrorResponse},
            409: {"model": ConversationErrorResponse},
            422: {"model": ConversationErrorResponse},
            503: {"model": ConversationErrorResponse},
        },
    )
    def post_conversation_message(
        conversation_id: str,
        message_request: AppendUserMessageRequest,
        actor: ActorContext = Depends(trusted_actor),
    ) -> ConversationMessageResponse | JSONResponse:
        parsed_conversation_id = _parse_conversation_id(conversation_id)
        if parsed_conversation_id is None:
            return _conversation_error_response(
                "conversation_not_found",
                status_code=404,
            )
        if conversation_service is None:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )
        try:
            command = AppendUserMessageCommand(
                owner_id=actor.owner_id,
                conversation_id=parsed_conversation_id,
                content=message_request.content,
            )
        except ValidationError:
            return _conversation_error_response(
                "request_invalid",
                status_code=422,
            )
        try:
            view = conversation_service.append_user_message(command)
            if (
                not isinstance(view, ConversationMessageView)
                or view.conversation_id != parsed_conversation_id
            ):
                raise TypeError("conversation service returned an invalid message")
            return ConversationMessageResponse.from_view(view)
        except ConversationServiceError as error:
            return _conversation_service_error(error)
        except Exception:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )

    @app.get(
        "/conversations/{conversation_id}/messages",
        response_model=ConversationMessagePageResponse,
        responses={
            404: {"model": ConversationErrorResponse},
            422: {"model": ConversationErrorResponse},
            503: {"model": ConversationErrorResponse},
        },
    )
    def get_conversation_messages(
        conversation_id: str,
        limit: int = Query(default=50, ge=1, le=100),
        after_sequence: int = Query(default=0, ge=0),
        actor: ActorContext = Depends(trusted_actor),
    ) -> ConversationMessagePageResponse | JSONResponse:
        parsed_conversation_id = _parse_conversation_id(conversation_id)
        if parsed_conversation_id is None:
            return _conversation_error_response(
                "conversation_not_found",
                status_code=404,
            )
        if conversation_service is None:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )
        try:
            page = conversation_service.list_messages(
                owner_id=actor.owner_id,
                conversation_id=parsed_conversation_id,
                limit=limit,
                after_sequence=after_sequence,
            )
            if (
                not isinstance(page, ConversationMessagePage)
                or page.limit != limit
                or page.after_sequence != after_sequence
                or any(
                    item.conversation_id != parsed_conversation_id
                    for item in page.items
                )
            ):
                raise TypeError("conversation service returned an invalid page")
            return ConversationMessagePageResponse.from_page(
                conversation_id=parsed_conversation_id,
                page=page,
            )
        except ConversationServiceError as error:
            return _conversation_service_error(error)
        except Exception:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )

    @app.post(
        "/conversations/{conversation_id}/archive",
        response_model=ConversationResponse,
        responses={
            404: {"model": ConversationErrorResponse},
            422: {"model": ConversationErrorResponse},
            503: {"model": ConversationErrorResponse},
        },
    )
    def archive_conversation(
        conversation_id: str,
        _empty_body: None = Depends(require_empty_body),
        actor: ActorContext = Depends(trusted_actor),
    ) -> ConversationResponse | JSONResponse:
        parsed_conversation_id = _parse_conversation_id(conversation_id)
        if parsed_conversation_id is None:
            return _conversation_error_response(
                "conversation_not_found",
                status_code=404,
            )
        if conversation_service is None:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )
        try:
            view = conversation_service.archive_conversation(
                owner_id=actor.owner_id,
                conversation_id=parsed_conversation_id,
            )
            if (
                not isinstance(view, ConversationView)
                or view.conversation_id != parsed_conversation_id
                or view.status.value != "archived"
            ):
                raise TypeError("conversation service returned an invalid archive")
            return ConversationResponse.from_view(view)
        except ConversationServiceError as error:
            return _conversation_service_error(error)
        except Exception:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )

    @app.post(
        "/conversations/{conversation_id}/hide",
        status_code=204,
        response_model=None,
        responses={
            404: {"model": ConversationErrorResponse},
            422: {"model": ConversationErrorResponse},
            503: {"model": ConversationErrorResponse},
        },
    )
    def hide_conversation(
        conversation_id: str,
        _empty_body: None = Depends(require_empty_body),
        actor: ActorContext = Depends(trusted_actor),
    ) -> Response:
        parsed_conversation_id = _parse_conversation_id(conversation_id)
        if parsed_conversation_id is None:
            return _conversation_error_response(
                "conversation_not_found",
                status_code=404,
            )
        if conversation_service is None:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )
        try:
            view = conversation_service.hide_conversation(
                owner_id=actor.owner_id,
                conversation_id=parsed_conversation_id,
            )
            if (
                not isinstance(view, ConversationView)
                or view.conversation_id != parsed_conversation_id
                or view.status.value != "hidden"
            ):
                raise TypeError("conversation service returned an invalid hide")
            return Response(status_code=204)
        except ConversationServiceError as error:
            return _conversation_service_error(error)
        except Exception:
            return _conversation_error_response(
                "service_unavailable",
                status_code=503,
            )

    @app.post(
        "/conversations/{conversation_id}/memory-candidates",
        status_code=201,
        response_model=MemoryCandidateResponse,
        responses={
            404: {"model": MemoryCandidateErrorResponse},
            409: {"model": MemoryCandidateErrorResponse},
            422: {"model": MemoryCandidateErrorResponse},
            503: {"model": MemoryCandidateErrorResponse},
        },
    )
    def post_memory_candidate(
        conversation_id: str,
        candidate_request: CreateMemoryCandidateRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
    ) -> MemoryCandidateResponse | JSONResponse:
        parsed_conversation_id = _parse_conversation_id(conversation_id)
        if parsed_conversation_id is None:
            return _memory_candidate_error_response(
                "conversation_not_found", status_code=404
            )
        if memory_candidate_service is None:
            return _memory_candidate_error_response(
                "service_unavailable", status_code=503
            )
        try:
            command = CreateMemoryCandidateCommand(
                owner_id=actor.owner_id,
                conversation_id=parsed_conversation_id,
                idempotency_key=idempotency_key,
                target_scope=TargetScope(candidate_request.target_scope),
                candidate_kind=CandidateKind(candidate_request.candidate_kind),
                memory_key=candidate_request.memory_key,
                operation=MemoryOperation(candidate_request.operation),
                proposal_payload=candidate_request.proposal_payload,
                provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
                producer_id="riftcoach-public-api",
                producer_version="1.0.0",
                proposal_confidence=None,
            )
            view = memory_candidate_service.create(command)
            if (
                not isinstance(view, MemoryCandidateView)
                or view.conversation_id != parsed_conversation_id
            ):
                raise TypeError("memory candidate service returned invalid view")
            return MemoryCandidateResponse.from_view(view)
        except MemoryCandidateServiceError as error:
            return _memory_candidate_service_error(error)
        except ValidationError:
            return _memory_candidate_error_response("request_invalid", status_code=422)
        except Exception:
            return _memory_candidate_error_response(
                "service_unavailable", status_code=503
            )

    @app.get(
        "/memory-candidates/{candidate_id}",
        response_model=MemoryCandidateResponse,
        responses={
            404: {"model": MemoryCandidateErrorResponse},
            503: {"model": MemoryCandidateErrorResponse},
        },
    )
    def get_memory_candidate(
        candidate_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> MemoryCandidateResponse | JSONResponse:
        parsed_candidate_id = _parse_candidate_id(candidate_id)
        if parsed_candidate_id is None:
            return _memory_candidate_error_response("candidate_not_found", status_code=404)
        if memory_candidate_service is None:
            return _memory_candidate_error_response("service_unavailable", status_code=503)
        try:
            view = memory_candidate_service.get(
                owner_id=actor.owner_id,
                candidate_id=parsed_candidate_id,
            )
            if not isinstance(view, MemoryCandidateView) or view.candidate_id != parsed_candidate_id:
                raise TypeError("memory candidate service returned invalid view")
            return MemoryCandidateResponse.from_view(view)
        except MemoryCandidateServiceError as error:
            return _memory_candidate_service_error(error)
        except Exception:
            return _memory_candidate_error_response("service_unavailable", status_code=503)

    @app.post(
        "/memory-candidates/{candidate_id}/accept",
        response_model=MemoryCandidateResponse,
        responses={
            404: {"model": MemoryCandidateErrorResponse},
            409: {"model": MemoryCandidateErrorResponse},
            422: {"model": MemoryCandidateErrorResponse},
            503: {"model": MemoryCandidateErrorResponse},
        },
    )
    def accept_memory_candidate(
        candidate_id: str,
        _empty: None = Depends(require_empty_body),
        actor: ActorContext = Depends(trusted_actor),
    ) -> MemoryCandidateResponse | JSONResponse:
        del _empty
        return _decide_memory_candidate(
            candidate_id=candidate_id,
            actor=actor,
            operation="accept",
        )

    @app.post(
        "/memory-candidates/{candidate_id}/reject",
        response_model=MemoryCandidateResponse,
        responses={
            404: {"model": MemoryCandidateErrorResponse},
            409: {"model": MemoryCandidateErrorResponse},
            422: {"model": MemoryCandidateErrorResponse},
            503: {"model": MemoryCandidateErrorResponse},
        },
    )
    def reject_memory_candidate(
        candidate_id: str,
        _empty: None = Depends(require_empty_body),
        actor: ActorContext = Depends(trusted_actor),
    ) -> MemoryCandidateResponse | JSONResponse:
        del _empty
        return _decide_memory_candidate(
            candidate_id=candidate_id,
            actor=actor,
            operation="reject",
        )

    def _decide_memory_candidate(
        *,
        candidate_id: str,
        actor: ActorContext,
        operation: str,
    ) -> MemoryCandidateResponse | JSONResponse:
        parsed_candidate_id = _parse_candidate_id(candidate_id)
        if parsed_candidate_id is None:
            return _memory_candidate_error_response("candidate_not_found", status_code=404)
        if memory_candidate_service is None:
            return _memory_candidate_error_response("service_unavailable", status_code=503)
        try:
            if operation == "accept":
                view = memory_candidate_service.accept(
                    owner_id=actor.owner_id,
                    candidate_id=parsed_candidate_id,
                    actor_id=actor.owner_id,
                )
            elif operation == "reject":
                view = memory_candidate_service.reject(
                    owner_id=actor.owner_id,
                    candidate_id=parsed_candidate_id,
                    actor_id=actor.owner_id,
                )
            else:
                raise TypeError("unsupported memory candidate decision")
            if not isinstance(view, MemoryCandidateView) or view.candidate_id != parsed_candidate_id:
                raise TypeError("memory candidate service returned invalid decision view")
            return MemoryCandidateResponse.from_view(view)
        except MemoryCandidateServiceError as error:
            return _memory_candidate_service_error(error)
        except Exception:
            return _memory_candidate_error_response("service_unavailable", status_code=503)

    def _typed_memory_query(
        *,
        operation: str,
        actor: ActorContext,
        relationship_id: UUID | None,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPageResponse | JSONResponse:
        if typed_memory_query_service is None:
            return _typed_memory_error_response("service_unavailable", status_code=503)
        try:
            if operation == "preferences":
                page = typed_memory_query_service.preferences(
                    owner_id=actor.owner_id,
                    include_history=include_history,
                    limit=limit,
                )
            elif operation == "profile" and relationship_id is not None:
                page = typed_memory_query_service.profile(
                    owner_id=actor.owner_id,
                    relationship_id=relationship_id,
                    include_history=include_history,
                    limit=limit,
                )
            elif operation == "reviews" and relationship_id is not None:
                page = typed_memory_query_service.reviews(
                    owner_id=actor.owner_id,
                    relationship_id=relationship_id,
                    include_history=include_history,
                    limit=limit,
                )
            else:
                raise TypeError("unsupported typed memory query")
            if not isinstance(page, TypedMemoryPage):
                raise TypeError("typed memory service returned invalid page")
            return TypedMemoryPageResponse.from_page(page)
        except TypedMemoryQueryServiceError as error:
            return _typed_memory_service_error(error)
        except Exception:
            return _typed_memory_error_response("service_unavailable", status_code=503)

    def _training_query(
        *,
        operation: str,
        actor: ActorContext,
        relationship_id: UUID,
        metric_key: str | None,
        include_history: bool,
        limit: int,
    ) -> TrainingPlanPageResponse | TrainingProgressPageResponse | JSONResponse:
        if training_query_service is None:
            return _training_error_response("service_unavailable", status_code=503)
        try:
            if operation == "plans":
                page = training_query_service.plans(
                    owner_id=actor.owner_id,
                    relationship_id=relationship_id,
                    include_history=include_history,
                    limit=limit,
                )
                if not isinstance(page, TrainingPlanPage):
                    raise TypeError("training service returned invalid Plan page")
                return TrainingPlanPageResponse.from_page(page)
            if operation == "progress":
                page = training_query_service.progress(
                    owner_id=actor.owner_id,
                    relationship_id=relationship_id,
                    metric_key=metric_key,
                    include_history=include_history,
                    limit=limit,
                )
                if not isinstance(page, TrainingProgressPage):
                    raise TypeError("training service returned invalid Progress page")
                return TrainingProgressPageResponse.from_page(page)
            raise TypeError("unsupported training query")
        except TrainingQueryServiceError as error:
            return _training_service_error(error)
        except Exception:
            return _training_error_response("service_unavailable", status_code=503)

    @app.get(
        "/memory/preferences",
        response_model=TypedMemoryPageResponse,
        responses={503: {"model": TypedMemoryErrorResponse}},
    )
    def get_memory_preferences(
        include_history: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> TypedMemoryPageResponse | JSONResponse:
        return _typed_memory_query(
            operation="preferences",
            actor=actor,
            relationship_id=None,
            include_history=include_history,
            limit=limit,
        )

    @app.get(
        "/memory/players/{relationship_id}/profile",
        response_model=TypedMemoryPageResponse,
        responses={
            404: {"model": TypedMemoryErrorResponse},
            503: {"model": TypedMemoryErrorResponse},
        },
    )
    def get_player_profile_memory(
        relationship_id: UUID,
        include_history: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> TypedMemoryPageResponse | JSONResponse:
        return _typed_memory_query(
            operation="profile",
            actor=actor,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
        )

    @app.get(
        "/memory/players/{relationship_id}/reviews",
        response_model=TypedMemoryPageResponse,
        responses={
            404: {"model": TypedMemoryErrorResponse},
            503: {"model": TypedMemoryErrorResponse},
        },
    )
    def get_player_review_memory(
        relationship_id: UUID,
        include_history: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> TypedMemoryPageResponse | JSONResponse:
        return _typed_memory_query(
            operation="reviews",
            actor=actor,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
        )

    @app.get(
        "/memory/players/{relationship_id}/training-plan",
        response_model=TrainingPlanPageResponse,
        responses={404: {"model": TrainingErrorResponse}, 503: {"model": TrainingErrorResponse}},
    )
    def get_training_plan(
        relationship_id: UUID,
        include_history: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> TrainingPlanPageResponse | JSONResponse:
        return _training_query(
            operation="plans",
            actor=actor,
            relationship_id=relationship_id,
            metric_key=None,
            include_history=include_history,
            limit=limit,
        )

    @app.get(
        "/memory/players/{relationship_id}/training-progress",
        response_model=TrainingProgressPageResponse,
        responses={404: {"model": TrainingErrorResponse}, 503: {"model": TrainingErrorResponse}},
    )
    def get_training_progress(
        relationship_id: UUID,
        metric_key: str | None = Query(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$"),
        include_history: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> TrainingProgressPageResponse | JSONResponse:
        return _training_query(
            operation="progress",
            actor=actor,
            relationship_id=relationship_id,
            metric_key=metric_key,
            include_history=include_history,
            limit=limit,
        )

    @app.get(
        "/owner-data/export",
        response_model=OwnerDataExportResponse,
        responses={
            409: {"model": LifecycleErrorResponse},
            503: {"model": LifecycleErrorResponse},
        },
    )
    def get_owner_data_export(
        actor: ActorContext = Depends(trusted_actor),
    ) -> OwnerDataExportResponse | JSONResponse:
        if owner_data_lifecycle_service is None:
            return _lifecycle_error_response(
                "lifecycle_unavailable", status_code=503
            )
        try:
            export = owner_data_lifecycle_service.export(owner_id=actor.owner_id)
            if not isinstance(export, OwnerDataExport) or export.owner_id != actor.owner_id:
                raise TypeError("lifecycle service returned invalid export")
            return OwnerDataExportResponse.from_export(export)
        except OwnerDataLifecycleError as error:
            return _lifecycle_service_error(error)
        except Exception:
            return _lifecycle_error_response(
                "lifecycle_unavailable", status_code=503
            )

    @app.post(
        "/owner-data/deletions",
        response_model=OwnerDataDeletionResponse,
        responses={
            202: {"model": OwnerDataDeletionResponse},
            404: {"model": LifecycleErrorResponse},
            409: {"model": LifecycleErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": LifecycleErrorResponse},
        },
    )
    def post_owner_data_deletion(
        delete_request: OwnerDataDeleteRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
    ) -> OwnerDataDeletionResponse | JSONResponse:
        if owner_data_lifecycle_service is None:
            return _lifecycle_error_response(
                "lifecycle_unavailable", status_code=503
            )
        try:
            command = OwnerDataDeleteCommand(
                owner_id=actor.owner_id,
                idempotency_key=idempotency_key,
                scope=OwnerDataDeleteScope(delete_request.scope),
                conversation_id=delete_request.conversation_id,
                relationship_id=delete_request.relationship_id,
                requested_at=datetime.now(timezone.utc),
            )
            marker = owner_data_lifecycle_service.delete(command)
            if not isinstance(marker, OwnerDataDeletionMarker):
                raise TypeError("lifecycle service returned invalid marker")
            response = OwnerDataDeletionResponse.from_marker(marker)
            if marker.status is OwnerDataDeletionStatus.CLEANUP_PENDING:
                return JSONResponse(
                    status_code=202,
                    content=response.model_dump(mode="json"),
                )
            return response
        except OwnerDataLifecycleError as error:
            return _lifecycle_service_error(error)
        except ValidationError:
            return _error_response("request_invalid", status_code=422)
        except Exception:
            return _lifecycle_error_response(
                "lifecycle_unavailable", status_code=503
            )

    @app.post(
        "/owner-data/deletions/{marker_id}/retry",
        response_model=OwnerDataDeletionResponse,
        responses={
            202: {"model": OwnerDataDeletionResponse},
            404: {"model": LifecycleErrorResponse},
            503: {"model": LifecycleErrorResponse},
        },
    )
    def retry_owner_data_deletion(
        marker_id: str,
        _empty_body: None = Depends(require_empty_body),
        actor: ActorContext = Depends(trusted_actor),
    ) -> OwnerDataDeletionResponse | JSONResponse:
        del _empty_body
        if owner_data_lifecycle_service is None:
            return _lifecycle_error_response(
                "lifecycle_unavailable", status_code=503
            )
        try:
            parsed_marker_id = UUID(marker_id)
        except (AttributeError, TypeError, ValueError):
            return _lifecycle_error_response("deletion_not_found", status_code=404)
        try:
            marker = owner_data_lifecycle_service.retry(
                owner_id=actor.owner_id,
                marker_id=parsed_marker_id,
            )
            if not isinstance(marker, OwnerDataDeletionMarker):
                raise TypeError("lifecycle service returned invalid marker")
            response = OwnerDataDeletionResponse.from_marker(marker)
            if marker.status is OwnerDataDeletionStatus.CLEANUP_PENDING:
                return JSONResponse(
                    status_code=202,
                    content=response.model_dump(mode="json"),
                )
            return response
        except OwnerDataLifecycleError as error:
            return _lifecycle_service_error(error)
        except Exception:
            return _lifecycle_error_response(
                "lifecycle_unavailable", status_code=503
            )

    @app.post(
        "/player-links",
        status_code=202,
        response_model=CreatePlayerLinkResponse,
        responses={
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def post_player_link(
        link_request: CreatePlayerLinkRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
    ) -> CreatePlayerLinkResponse | JSONResponse:
        started = time.perf_counter()
        try:
            command = CreatePlayerLinkCommand(
                owner_id=actor.owner_id,
                idempotency_key=idempotency_key,
                riot_id=link_request.riot_id,
                routing_region=RoutingRegion(link_request.routing_region),
                relationship_role=RelationshipRole(
                    link_request.relationship_role
                ),
            )
            result = player_link_service.create(command)
            if not isinstance(result, PlayerLinkCreateResult):
                raise TypeError("player link service returned an invalid result")
            task = result.task
            response = CreatePlayerLinkResponse(
                disposition=result.disposition,
                link_task_id=task.link_task_id,
                status=task.status,
                link=f"/player-links/{task.link_task_id}",
            )
            if observability is not None:
                observability.emit(
                    "api.player_link_created",
                    {
                        "task_id": str(task.link_task_id),
                        "status": 202,
                        "disposition": result.disposition.value,
                        "latency_ms": max(
                            0.0,
                            (time.perf_counter() - started) * 1000,
                        ),
                    },
                )
            return response
        except PlayerLinkServiceError as error:
            status_code, code = _CREATE_PLAYER_LINK_STATUS.get(
                error.code,
                (503, "service_unavailable"),
            )
            return _error_response(code, status_code=status_code)
        except ValidationError:
            return _error_response("request_invalid", status_code=422)
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/player-profiles",
        response_model=PlayerProfilePageResponse,
        responses={
            503: {"model": ErrorResponse},
        },
    )
    def get_player_profiles(
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> PlayerProfilePageResponse | JSONResponse:
        try:
            page = player_link_service.list_profiles(
                owner_id=actor.owner_id,
                limit=limit,
            )
            if not isinstance(page, PlayerProfilePage) or page.limit != limit:
                raise TypeError("player link service returned an invalid profile page")
            return PlayerProfilePageResponse.from_page(page)
        except PlayerLinkServiceError:
            return _error_response("service_unavailable", status_code=503)
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/player-profiles/{player_profile_id}/reviews/recent/latest",
        response_model=LatestProfileReviewResponse,
        responses={
            404: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_latest_profile_review(
        player_profile_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> LatestProfileReviewResponse | JSONResponse:
        try:
            parsed_profile_id = UUID(player_profile_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response(
                "player_profile_not_found",
                status_code=404,
            )
        if latest_profile_review_service is None:
            return _error_response("service_unavailable", status_code=503)
        try:
            result = latest_profile_review_service.get_latest(
                owner_id=actor.owner_id,
                player_profile_id=parsed_profile_id,
            )
            if (
                not isinstance(result, LatestProfileReviewResult)
                or result.player_profile_id != parsed_profile_id
            ):
                raise TypeError("latest review service returned invalid identity")
            return LatestProfileReviewResponse.from_result(result)
        except LatestProfileReviewServiceError as error:
            if error.code == "player_profile_not_found":
                return _error_response(
                    "player_profile_not_found",
                    status_code=404,
                )
            return _error_response("service_unavailable", status_code=503)
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/player-links/{link_task_id}",
        response_model=PlayerLinkResponse,
        responses={
            404: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_player_link(
        link_task_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> PlayerLinkResponse | JSONResponse:
        try:
            parsed_link_task_id = UUID(link_task_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("player_link_not_found", status_code=404)
        try:
            view = player_link_service.get_link(
                owner_id=actor.owner_id,
                link_task_id=parsed_link_task_id,
            )
            if (
                not isinstance(view, PlayerLinkTaskView)
                or view.link_task_id != parsed_link_task_id
            ):
                raise TypeError("player link service returned an invalid view")
            return PlayerLinkResponse.from_view(view)
        except PlayerLinkServiceError as error:
            if error.code == "link_not_found":
                return _error_response("player_link_not_found", status_code=404)
            return _error_response("service_unavailable", status_code=503)
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.post(
        "/conversations/{conversation_id}/reviews/recent",
        status_code=202,
        response_model=CreateConversationReviewTaskResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def post_conversation_recent_review(
        conversation_id: str,
        product_request: ConversationRecentReviewRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
    ) -> CreateConversationReviewTaskResponse | JSONResponse:
        try:
            parsed_conversation_id = UUID(conversation_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("conversation_not_found", status_code=404)

        create = getattr(task_service, "create_conversation_review", None)
        if not callable(create):
            return _error_response("service_unavailable", status_code=503)
        try:
            result = create(
                CreateConversationReviewTaskCommand(
                    owner_id=actor.owner_id,
                    idempotency_key=idempotency_key,
                    conversation_id=parsed_conversation_id,
                    request=product_request,
                )
            )
            if (
                not isinstance(result, TaskCreateResult)
                or result.task.schema_version != "2.0"
            ):
                raise TypeError("task service returned an invalid v2 result")
            task = result.task
            return CreateConversationReviewTaskResponse(
                disposition=result.disposition,
                conversation_id=parsed_conversation_id,
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
            if error.code == "conversation_not_found":
                return _error_response(
                    "conversation_not_found",
                    status_code=404,
                )
            status_code, code = _CREATE_TASK_STATUS.get(
                error.code,
                (503, "service_unavailable"),
            )
            return _error_response(code, status_code=status_code)
        except ValidationError:
            return _error_response("request_invalid", status_code=422)
        except Exception:
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

    @app.post(
        "/tasks/{task_id}/cancel",
        response_model=CancelTaskResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def cancel_task(
        task_id: str,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=_IDEMPOTENCY_PATTERN,
        ),
        actor: ActorContext = Depends(trusted_actor),
        _empty_body: None = Depends(require_empty_body),
    ) -> CancelTaskResponse | JSONResponse:
        del _empty_body
        try:
            parsed_task_id = UUID(task_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("task_not_found", status_code=404)
        cancel = getattr(task_service, "request_cancel", None)
        if not callable(cancel):
            return _error_response("service_unavailable", status_code=503)
        try:
            result = cancel(
                owner_id=actor.owner_id,
                task_id=parsed_task_id,
                request_id=idempotency_key,
            )
            if not isinstance(result, TaskCancelResult):
                raise TypeError("task service returned an invalid cancel result")
            return CancelTaskResponse.from_result(result)
        except TaskServiceError as error:
            return _task_lookup_error(error, not_found_code="task_not_found")
        except Exception as error:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/tasks/{task_id}/events",
        response_model=TaskEventPageResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_task_events(
        task_id: str,
        after_cursor: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=100),
        actor: ActorContext = Depends(trusted_actor),
    ) -> TaskEventPageResponse | JSONResponse:
        try:
            parsed_task_id = UUID(task_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("task_not_found", status_code=404)
        read_events = getattr(task_service, "read_events", None)
        if not callable(read_events):
            return _error_response("service_unavailable", status_code=503)
        try:
            page = read_events(
                owner_id=actor.owner_id,
                task_id=parsed_task_id,
                after_cursor=after_cursor,
                limit=limit,
            )
            if not isinstance(page, TaskEventPage):
                raise TypeError("task service returned an invalid event page")
            return TaskEventPageResponse.from_page(
                task_id=parsed_task_id,
                page=page,
            )
        except TaskServiceError as error:
            return _task_lookup_error(error, not_found_code="task_not_found")
        except Exception:
            return _error_response("service_unavailable", status_code=503)

    @app.get(
        "/tasks/{task_id}/events/stream",
        response_model=None,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def stream_task_events(
        task_id: str,
        after_cursor: int | None = Query(default=None, ge=0),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        actor: ActorContext = Depends(trusted_actor),
    ) -> StreamingResponse | JSONResponse:
        try:
            parsed_task_id = UUID(task_id)
        except (AttributeError, TypeError, ValueError):
            return _error_response("task_not_found", status_code=404)
        try:
            cursor = resolve_event_cursor(
                after_cursor=after_cursor,
                last_event_id=last_event_id,
            )
        except (TypeError, ValueError):
            return _error_response("request_invalid", status_code=422)
        if task_event_stream_service is None:
            return _error_response("service_unavailable", status_code=503)
        try:
            task = task_event_stream_service.preflight(
                owner_id=actor.owner_id,
                task_id=parsed_task_id,
            )
            if not isinstance(task, ReviewTaskView) or task.task_id != parsed_task_id:
                raise TaskEventStreamServiceError("service_unavailable")
        except TaskEventStreamServiceError as error:
            if error.code == "task_not_found":
                return _error_response("task_not_found", status_code=404)
            return _error_response("service_unavailable", status_code=503)
        except Exception:
            return _error_response("service_unavailable", status_code=503)
        return StreamingResponse(
            task_event_stream_service.stream(
                owner_id=actor.owner_id,
                task_id=parsed_task_id,
                after_cursor=cursor,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

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
        "/runs/{run_id}/evidence",
        response_model=EvidenceSnapshotResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_run_evidence(
        run_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> EvidenceSnapshotResponse | JSONResponse:
        if evidence_product_service is None:
            return _error_response(
                "evidence_unavailable",
                status_code=503,
                run_id=run_id,
            )
        try:
            view = evidence_product_service.get_evidence(
                owner_id=actor.owner_id,
                run_id=run_id,
            )
            if not isinstance(view, EvidenceSnapshotView) or view.run_id != run_id:
                raise TypeError("evidence service returned an invalid identity")
            return EvidenceSnapshotResponse.from_view(view)
        except EvidenceProductServiceError as error:
            return _evidence_product_error(error, run_id=run_id)
        except Exception:
            return _error_response(
                "evidence_integrity_failed",
                status_code=500,
                run_id=run_id,
            )

    @app.get(
        "/runs/{run_id}/product-state",
        response_model=ProductStateResponse,
        responses={
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_run_product_state(
        run_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> ProductStateResponse | JSONResponse:
        if evidence_product_service is None:
            return _error_response(
                "evidence_unavailable",
                status_code=503,
                run_id=run_id,
            )
        try:
            state = evidence_product_service.get_product_state(
                owner_id=actor.owner_id,
                run_id=run_id,
            )
            if not isinstance(state, ProductRunState) or state.run_id != run_id:
                raise TypeError("product service returned an invalid identity")
            return ProductStateResponse.from_state(state)
        except EvidenceProductServiceError as error:
            return _evidence_product_error(error, run_id=run_id)
        except Exception:
            return _error_response(
                "evidence_integrity_failed",
                status_code=500,
                run_id=run_id,
            )

    @app.get(
        "/runs/{run_id}/recent-summary",
        response_model=RecentSummaryResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    def get_recent_summary(
        run_id: str,
        actor: ActorContext = Depends(trusted_actor),
    ) -> RecentSummaryResponse | JSONResponse:
        task = owned_run_task(actor, run_id)
        if isinstance(task, JSONResponse):
            return task
        if task.status in {
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.RECOVERY_REQUIRED,
        }:
            return _error_response(
                "run_not_ready",
                status_code=409,
                run_id=task.run_id,
            )
        if task.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
            return _error_response(
                "run_not_available",
                status_code=409,
                run_id=task.run_id,
            )
        if not task.report_available:
            return _error_response(
                "report_not_available",
                status_code=409,
                run_id=task.run_id,
            )
        get_summary = getattr(query_service, "get_recent_summary", None)
        if not callable(get_summary):
            return _error_response(
                "service_unavailable",
                status_code=503,
                run_id=task.run_id,
            )
        try:
            result = get_summary(task.run_id)
            if (
                not isinstance(result, RecentSummaryView)
                or result.run_id != task.run_id
                or task.publication_status is None
                or result.publication_status.value
                != task.publication_status.value
            ):
                raise ValueError("recent Summary identity mismatch")
            return RecentSummaryResponse.from_view(result)
        except RunQueryError as error:
            if error.code == "report_not_available":
                return _error_response(
                    "report_not_available",
                    status_code=409,
                    run_id=task.run_id,
                )
            return _error_response(
                "run_integrity_failed",
                status_code=500,
                run_id=task.run_id,
            )
        except Exception:
            return _error_response(
                "run_integrity_failed",
                status_code=500,
                run_id=task.run_id,
            )

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
        if task.status in {
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.RECOVERY_REQUIRED,
        }:
            return _error_response(
                "run_not_ready",
                status_code=409,
                run_id=task.run_id,
            )
        if task.status in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
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
        if task.status in {
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.RECOVERY_REQUIRED,
        }:
            return _error_response(
                "run_not_ready",
                status_code=409,
                run_id=task.run_id,
            )
        if task.status in {
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        } or not task.report_available:
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
    "ConversationServicePort",
    "ReadinessPort",
    "PlayerLinkServicePort",
    "RunQueryPort",
    "TaskDeletionPort",
    "TaskServicePort",
    "create_app",
]
