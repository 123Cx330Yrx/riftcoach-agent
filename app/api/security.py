"""Small, explicit HTTP security-header boundary for the API adapter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)


@dataclass(frozen=True, slots=True)
class RequestBudget:
    """Single-node HTTP budgets; edge remains the first enforcement layer."""

    max_body_bytes: int = 1_048_576
    max_header_bytes: int = 16_384
    rate_limit: int = 60
    rate_window_seconds: int = 60

    def __post_init__(self) -> None:
        if self.max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        if self.max_header_bytes <= 0:
            raise ValueError("max_header_bytes must be positive")
        if self.rate_limit <= 0:
            raise ValueError("rate_limit must be positive")
        if self.rate_window_seconds <= 0:
            raise ValueError("rate_window_seconds must be positive")


class InMemoryRateLimiter:
    """Development/single-node limiter; no multi-replica claim."""

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("rate limiter values must be positive")
        self._limit = limit
        self._window = timedelta(seconds=window_seconds)
        self._clock = clock
        self._buckets: dict[str, tuple[datetime, int]] = {}

    def allow(self, key: str) -> bool:
        now = self._clock()
        started, count = self._buckets.get(key, (now, 0))
        if now - started >= self._window:
            started, count = now, 0
        if count >= self._limit:
            self._buckets[key] = (started, count)
            return False
        self._buckets[key] = (started, count + 1)
        return True


async def _send_budget_error(send, *, status_code: int, code: str) -> None:
    body = json.dumps({"code": code}, separators=(",", ":")).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                *[
                    (name.lower().encode("ascii"), value.encode("ascii"))
                    for name, value in security_headers().items()
                ],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class _RequestBodyExceeded(RuntimeError):
    pass


class RequestBudgetMiddleware:
    """Bound headers/body and optional single-node IP rate policy."""

    def __init__(
        self,
        app,
        *,
        budget: RequestBudget,
        rate_limiter: InMemoryRateLimiter | None = None,
    ) -> None:
        self.app = app
        self.budget = budget
        self.rate_limiter = rate_limiter

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        header_size = sum(len(name) + len(value) for name, value in scope.get("headers", []))
        if header_size > self.budget.max_header_bytes:
            await _send_budget_error(
                send,
                status_code=431,
                code="request_headers_too_large",
            )
            return

        if self.rate_limiter is not None:
            client = scope.get("client")
            key = client[0] if isinstance(client, (tuple, list)) and client else "unknown"
            if not self.rate_limiter.allow(str(key)):
                await _send_budget_error(send, status_code=429, code="rate_limited")
                return

        content_length = next(
            (
                value
                for name, value in scope.get("headers", [])
                if name.lower() == b"content-length"
            ),
            None,
        )
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except (TypeError, ValueError):
                declared_length = self.budget.max_body_bytes + 1
            if declared_length > self.budget.max_body_bytes:
                await _send_budget_error(
                    send,
                    status_code=413,
                    code="request_body_too_large",
                )
                return

        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message.get("type") == "http.request":
                total += len(message.get("body", b""))
                if total > self.budget.max_body_bytes:
                    raise _RequestBodyExceeded()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestBodyExceeded:
            await _send_budget_error(
                send,
                status_code=413,
                code="request_body_too_large",
            )


def security_headers(*, include_hsts: bool = False) -> Mapping[str, str]:
    headers = {
        "Content-Security-Policy": _CSP,
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    }
    if include_hsts:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply headers at the API boundary; TLS/HSTS remains an edge concern."""

    def __init__(self, app, *, include_hsts: bool = False) -> None:
        super().__init__(app)
        self._headers = security_headers(include_hsts=include_hsts)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in self._headers.items():
            response.headers.setdefault(name, value)
        return response


__all__ = [
    "InMemoryRateLimiter",
    "RequestBudget",
    "RequestBudgetMiddleware",
    "SecurityHeadersMiddleware",
    "security_headers",
]
