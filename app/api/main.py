"""Thin FastAPI adapter for the first recent-review product slice.

This module owns HTTP concerns only.  It deliberately receives already-built
application/query services instead of constructing Riot clients, Providers,
Prompt Programs, or Runtime/Harness objects during import or app creation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, TypeAlias

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict

from app.product.recent_review import RecentReviewProductRequest
from app.product.recent_review_service import (
    RecentReviewApplicationError,
    RecentReviewApplicationResult,
)
from app.product.run_query import RunQueryError, RunView
from app.skills.recent_form_review import RecentFormReviewOutput


class ReviewServicePort(Protocol):
    def review(
        self,
        request: RecentReviewProductRequest,
    ) -> RecentReviewApplicationResult: ...


class RunQueryPort(Protocol):
    def get_run(self, run_id: str) -> RunView: ...

    def get_report(self, run_id: str) -> str: ...


class ApiLinks(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run: str
    report: str


class RecentReviewHttpResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    runtime_status: Literal["completed"]
    publication_status: Literal["published", "degraded", "rejected"]
    terminal_reason: str
    output: RecentFormReviewOutput
    links: ApiLinks


ApiErrorCode: TypeAlias = Literal[
    "request_invalid",
    "player_not_found",
    "insufficient_match_data",
    "riot_authentication_failed",
    "riot_rate_limited",
    "upstream_timeout",
    "upstream_unavailable",
    "service_configuration_invalid",
    "review_runtime_failed",
    "run_not_found",
    "report_not_available",
    "run_integrity_failed",
]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: ApiErrorCode
    run_id: str | None = None
    terminal_reason: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: Literal["ok"] = "ok"
    api_version: Literal["1.0"] = "1.0"
    schema_version: Literal["1.0"] = "1.0"


_APPLICATION_STATUS: Mapping[str, int] = {
    "player_not_found": 404,
    "insufficient_match_data": 422,
    "riot_authentication_failed": 503,
    "riot_rate_limited": 503,
    "upstream_timeout": 504,
    "upstream_unavailable": 503,
    "service_configuration_invalid": 503,
    "review_runtime_failed": 500,
}
_QUERY_STATUS: Mapping[str, int] = {
    "run_not_found": 404,
    "report_not_available": 409,
    "run_integrity_failed": 500,
}


def _error_response(
    payload: Mapping[str, Any],
    *,
    status_code: int,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    """Return only the allowlisted public error fields."""

    body = ErrorResponse(
        code=payload.get("code"),
        run_id=payload.get("run_id"),
        terminal_reason=payload.get("terminal_reason"),
    ).model_dump(mode="json", exclude_none=True)
    headers: dict[str, str] = {}
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _application_error_response(error: RecentReviewApplicationError) -> JSONResponse:
    status_code = _APPLICATION_STATUS.get(error.code, 500)
    public = error.to_public_dict()
    retry_after = public.get("retry_after_seconds")
    return _error_response(
        public,
        status_code=status_code,
        retry_after_seconds=(
            retry_after if isinstance(retry_after, int) else None
        ),
    )


def _query_error_response(error: RunQueryError) -> JSONResponse:
    return _error_response(
        error.to_public_dict(),
        status_code=_QUERY_STATUS.get(error.code, 500),
    )


def create_app(
    *,
    review_service: ReviewServicePort,
    query_service: RunQueryPort,
) -> FastAPI:
    """Create the local V1 API from explicit application/query ports.

    No dependency construction occurs here.  This is intentional: importing
    the module and generating OpenAPI must not read a Key or make network I/O.
    """

    if not callable(getattr(review_service, "review", None)):
        raise TypeError("review_service must expose review()")
    if not callable(getattr(query_service, "get_run", None)):
        raise TypeError("query_service must expose get_run()")
    if not callable(getattr(query_service, "get_report", None)):
        raise TypeError("query_service must expose get_report()")

    app = FastAPI(
        title="RiftCoach Agent API",
        version="1.0",
        description="Local thin HTTP adapter for the recent-review product slice.",
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # Request details may contain untrusted Riot ID text.  The public
        # contract intentionally exposes only the stable error code.
        del request, exc
        return _error_response({"code": "request_invalid"}, status_code=422)

    @app.post(
        "/reviews/recent",
        status_code=201,
        response_model=RecentReviewHttpResponse,
        responses={
            422: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    def post_recent_review(
        product_request: RecentReviewProductRequest,
    ) -> RecentReviewHttpResponse | JSONResponse:
        try:
            result = review_service.review(product_request)
            if not isinstance(result, RecentReviewApplicationResult):
                raise RuntimeError("application service returned an invalid result")
            return RecentReviewHttpResponse(
                run_id=result.run_id,
                runtime_status=result.runtime_status.value,
                publication_status=result.publication_status.value,
                terminal_reason=result.terminal_reason,
                output=result.output,
                links=ApiLinks(
                    run=f"/runs/{result.run_id}",
                    report=f"/runs/{result.run_id}/report",
                ),
            )
        except RecentReviewApplicationError as error:
            return _application_error_response(error)
        except Exception:
            # Never serialize an internal exception, URL, path or Provider
            # response.  The service has already lost the unsafe details.
            return _error_response(
                {"code": "review_runtime_failed"},
                status_code=500,
            )

    @app.get(
        "/runs/{run_id}",
        response_model=RunView,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def get_run(run_id: str) -> RunView | JSONResponse:
        try:
            return query_service.get_run(run_id)
        except RunQueryError as error:
            return _query_error_response(error)
        except Exception:
            return _error_response(
                {"code": "run_integrity_failed"},
                status_code=500,
            )

    @app.get(
        "/runs/{run_id}/report",
        response_model=None,
        response_class=Response,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def get_report(run_id: str) -> Response:
        try:
            report = query_service.get_report(run_id)
            if not isinstance(report, str) or not report:
                raise ValueError("query service returned invalid report")
            return Response(content=report, media_type="text/markdown")
        except RunQueryError as error:
            return _query_error_response(error)
        except Exception:
            return _error_response(
                {"code": "run_integrity_failed"},
                status_code=500,
            )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    return app


__all__ = [
    "ApiLinks",
    "ApiErrorCode",
    "ErrorResponse",
    "HealthResponse",
    "RecentReviewHttpResponse",
    "RunQueryPort",
    "ReviewServicePort",
    "create_app",
]
