"""Reliable synchronous execution pipeline for registered local tools."""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Mapping

from app.runtime.observer import RuntimeObservationError

from .cache import TTLCache, make_cache_key
from .circuit_breaker import CircuitBreakerRegistry
from .errors import (
    ToolError,
    ToolInputValidationError,
    ToolNotFoundError,
    ToolOutputValidationError,
)
from .metrics import ToolMetrics
from .models import ToolContext, ToolDefinition, ToolErrorInfo, ToolResult
from .registry import ToolRegistry
from .schema import validate_tool_input, validate_tool_output


class ToolRuntime:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        cache: TTLCache | None = None,
        breakers: CircuitBreakerRegistry | None = None,
        metrics: ToolMetrics | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        call_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        self.registry = registry
        self.cache = cache if cache is not None else TTLCache(clock=clock)
        self.breakers = (
            breakers
            if breakers is not None
            else CircuitBreakerRegistry(clock=clock)
        )
        self.metrics = metrics if metrics is not None else ToolMetrics()
        self._clock = clock
        self._sleep = sleep
        self._call_id_factory = call_id_factory

    def execute(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        *,
        metadata: Mapping[str, Any] | None = None,
        timeout_cap_s: float | None = None,
    ) -> ToolResult:
        if timeout_cap_s is not None and (
            isinstance(timeout_cap_s, bool)
            or not isinstance(timeout_cap_s, (int, float))
            or timeout_cap_s <= 0
        ):
            raise ValueError("timeout_cap_s must be greater than zero or None")
        started_at = self._clock()
        call_id = self._call_id_factory()
        self.metrics.increment(tool_name, "calls")

        try:
            definition = self.registry.get(tool_name)
        except ToolNotFoundError as exc:
            return self._failure(
                tool_name=tool_name,
                tool_version="0.0.0",
                call_id=call_id,
                attempts=0,
                started_at=started_at,
                error=self._safe_error(exc),
            )

        try:
            validate_tool_input(definition, params)
        except ToolInputValidationError as exc:
            return self._failure(
                tool_name=definition.name,
                tool_version=definition.version,
                call_id=call_id,
                attempts=0,
                started_at=started_at,
                error=self._safe_error(exc),
            )

        cache_key = make_cache_key(
            definition.name,
            definition.version,
            params,
        )
        if definition.policy.cache.ttl_s > 0:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.metrics.increment(definition.name, "cache_hits")
                latency_ms = self._finish_latency(
                    definition.name, started_at
                )
                return ToolResult.ok(
                    data=cached_data,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    call_id=call_id,
                    attempts=0,
                    latency_ms=latency_ms,
                    cached=True,
                )

        timeout_s = min(
            definition.policy.timeout_s,
            timeout_cap_s
            if timeout_cap_s is not None
            else definition.policy.timeout_s,
        )
        deadline = started_at + timeout_s
        breaker = self.breakers.get(
            definition.name,
            definition.policy.circuit_breaker,
        )
        if not breaker.allow_call():
            self.metrics.increment(definition.name, "circuit_rejections")
            upstream_error = ToolErrorInfo(
                code="circuit_open",
                message="tool execution blocked by open circuit",
                retryable=True,
            )
            return self._fallback_or_failure(
                definition=definition,
                params=params,
                call_id=call_id,
                attempts=0,
                deadline=deadline,
                metadata=metadata,
                started_at=started_at,
                upstream_error=upstream_error,
                cause=RuntimeError("circuit_open"),
            )

        attempts = 0
        last_error: ToolErrorInfo | None = None
        last_exception: Exception | None = None

        while attempts < definition.policy.retry.max_attempts:
            if self._clock() >= deadline:
                budget_error = ToolErrorInfo(
                    code="retry_budget_exhausted",
                    message="tool execution budget exhausted",
                    retryable=False,
                )
                return self._fallback_or_failure(
                    definition=definition,
                    params=params,
                    call_id=call_id,
                    attempts=attempts,
                    deadline=deadline,
                    metadata=metadata,
                    started_at=started_at,
                    upstream_error=last_error,
                    cause=last_exception or RuntimeError("deadline"),
                    terminal_error=budget_error,
                )

            attempts += 1
            context = ToolContext(
                call_id=call_id,
                attempt=attempts,
                deadline_monotonic=deadline,
                metadata=metadata or {},
                clock=self._clock,
            )

            try:
                data = definition.handler(params, context)
                validate_tool_output(definition, data)
            except RuntimeObservationError:
                raise
            except ToolOutputValidationError as exc:
                breaker.record_failure(count_toward_threshold=False)
                return self._failure(
                    tool_name=definition.name,
                    tool_version=definition.version,
                    call_id=call_id,
                    attempts=attempts,
                    started_at=started_at,
                    error=self._safe_error(exc),
                )
            except Exception as exc:
                last_exception = exc
                last_error = self._safe_error(exc)
                breaker.record_failure(
                    count_toward_threshold=last_error.retryable
                )

                if (
                    not last_error.retryable
                    or attempts >= definition.policy.retry.max_attempts
                ):
                    return self._fallback_or_failure(
                        definition=definition,
                        params=params,
                        call_id=call_id,
                        attempts=attempts,
                        deadline=deadline,
                        metadata=metadata,
                        started_at=started_at,
                        upstream_error=last_error,
                        cause=exc,
                    )

                delay = self._retry_delay(definition, attempts)
                remaining = max(0.0, deadline - self._clock())
                if delay >= remaining:
                    budget_error = ToolErrorInfo(
                        code="retry_budget_exhausted",
                        message="tool retry budget exhausted",
                        retryable=False,
                    )
                    return self._fallback_or_failure(
                        definition=definition,
                        params=params,
                        call_id=call_id,
                        attempts=attempts,
                        deadline=deadline,
                        metadata=metadata,
                        started_at=started_at,
                        upstream_error=last_error,
                        cause=exc,
                        terminal_error=budget_error,
                    )

                self.metrics.increment(definition.name, "retries")
                self._sleep(delay)
                continue

            breaker.record_success()
            if definition.policy.cache.ttl_s > 0:
                self.cache.set(
                    cache_key,
                    data,
                    ttl_s=definition.policy.cache.ttl_s,
                )
            self.metrics.increment(definition.name, "upstream_successes")
            latency_ms = self._finish_latency(definition.name, started_at)
            return ToolResult.ok(
                data=data,
                tool_name=definition.name,
                tool_version=definition.version,
                call_id=call_id,
                attempts=attempts,
                latency_ms=latency_ms,
            )

        raise AssertionError("retry loop exited without a result")

    def _fallback_or_failure(
        self,
        *,
        definition: ToolDefinition,
        params: Mapping[str, Any],
        call_id: str,
        attempts: int,
        deadline: float,
        metadata: Mapping[str, Any] | None,
        started_at: float,
        upstream_error: ToolErrorInfo | None,
        cause: Exception,
        terminal_error: ToolErrorInfo | None = None,
    ) -> ToolResult:
        if definition.fallback is None:
            return self._failure(
                tool_name=definition.name,
                tool_version=definition.version,
                call_id=call_id,
                attempts=attempts,
                started_at=started_at,
                error=terminal_error
                or upstream_error
                or ToolErrorInfo(
                    code="tool_execution_failed",
                    message="tool execution failed",
                ),
                upstream_error=upstream_error
                if terminal_error is not None
                else None,
            )

        context = ToolContext(
            call_id=call_id,
            attempt=max(1, attempts),
            deadline_monotonic=deadline,
            metadata=metadata or {},
            clock=self._clock,
        )
        try:
            data = definition.fallback(params, context, cause)
            validate_tool_output(definition, data)
        except RuntimeObservationError:
            raise
        except Exception:
            return self._failure(
                tool_name=definition.name,
                tool_version=definition.version,
                call_id=call_id,
                attempts=attempts,
                started_at=started_at,
                error=ToolErrorInfo(
                    code="fallback_failed",
                    message="tool fallback failed",
                    retryable=False,
                ),
                upstream_error=upstream_error,
            )

        self.metrics.increment(definition.name, "fallback_successes")
        latency_ms = self._finish_latency(definition.name, started_at)
        return ToolResult.ok(
            data=data,
            tool_name=definition.name,
            tool_version=definition.version,
            call_id=call_id,
            attempts=attempts,
            latency_ms=latency_ms,
            fallback_used=True,
            upstream_error=upstream_error,
        )

    def _failure(
        self,
        *,
        tool_name: str,
        tool_version: str,
        call_id: str,
        attempts: int,
        started_at: float,
        error: ToolErrorInfo,
        upstream_error: ToolErrorInfo | None = None,
    ) -> ToolResult:
        self.metrics.increment(tool_name, "failures")
        latency_ms = self._finish_latency(tool_name, started_at)
        return ToolResult.fail(
            error=error,
            tool_name=tool_name,
            tool_version=tool_version,
            call_id=call_id,
            attempts=attempts,
            latency_ms=latency_ms,
            upstream_error=upstream_error,
        )

    def _finish_latency(self, tool_name: str, started_at: float) -> float:
        latency_ms = max(0.0, (self._clock() - started_at) * 1000)
        self.metrics.observe_latency(tool_name, latency_ms)
        return latency_ms

    @staticmethod
    def _retry_delay(definition: ToolDefinition, attempts: int) -> float:
        retry = definition.policy.retry
        return min(
            retry.max_delay_s,
            retry.base_delay_s * (2 ** (attempts - 1)),
        )

    @staticmethod
    def _safe_error(exc: Exception) -> ToolErrorInfo:
        code = getattr(exc, "code", None) or "tool_execution_failed"
        retryable = bool(getattr(exc, "retryable", False))
        if isinstance(exc, ToolError):
            message = "tool contract rejected the operation"
        elif retryable:
            message = "tool dependency temporarily failed"
        else:
            message = "tool execution failed"
        return ToolErrorInfo(
            code=str(code),
            message=message,
            retryable=retryable,
        )
