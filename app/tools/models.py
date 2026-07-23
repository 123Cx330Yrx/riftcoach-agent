"""Core contracts shared by tool authors, the registry, and the runtime."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


ToolHandler = Callable[[Mapping[str, Any], "ToolContext"], Mapping[str, Any]]
ToolFallback = Callable[[Mapping[str, Any], "ToolContext", Exception], Mapping[str, Any]]

_TOOL_NAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$"
)
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    base_delay_s: float = 0.0
    max_delay_s: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if self.base_delay_s < 0:
            raise ValueError("base_delay_s cannot be negative")
        if self.max_delay_s < self.base_delay_s:
            raise ValueError("max_delay_s cannot be less than base_delay_s")


@dataclass(frozen=True)
class CachePolicy:
    ttl_s: float = 0.0

    def __post_init__(self) -> None:
        if self.ttl_s < 0:
            raise ValueError("ttl_s cannot be negative")


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 5
    recovery_s: float = 60.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_s <= 0:
            raise ValueError("recovery_s must be positive")


@dataclass(frozen=True)
class ToolPolicy:
    timeout_s: float = 30.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    cache: CachePolicy = field(default_factory=CachePolicy)
    circuit_breaker: CircuitBreakerPolicy = field(
        default_factory=CircuitBreakerPolicy
    )

    def __post_init__(self) -> None:
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")


@dataclass(frozen=True)
class ToolContext:
    """Execution metadata kept separate from business parameters."""

    call_id: str
    attempt: int
    deadline_monotonic: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("call_id cannot be blank")
        if self.attempt < 1:
            raise ValueError("attempt must be at least 1")
        if self.deadline_monotonic <= 0:
            raise ValueError("deadline_monotonic must be positive")

    def remaining_s(self, *, now_monotonic: float | None = None) -> float:
        now = time.monotonic() if now_monotonic is None else now_monotonic
        return max(0.0, self.deadline_monotonic - now)


@dataclass(frozen=True)
class ToolErrorInfo:
    code: str
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("error code cannot be blank")
        if not self.message.strip():
            raise ValueError("error message cannot be blank")


@dataclass(frozen=True)
class ToolDefinition:
    """Machine-readable manual for one stable tool name."""

    name: str
    version: str
    description: str
    handler: ToolHandler
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    policy: ToolPolicy = field(default_factory=ToolPolicy)
    idempotent: bool = True
    fallback: ToolFallback | None = None

    def __post_init__(self) -> None:
        if not _TOOL_NAME_PATTERN.fullmatch(self.name):
            raise ValueError(
                "tool name must be a dotted lowercase namespace, "
                "for example 'riot.recent_matches'"
            )
        if not _VERSION_PATTERN.fullmatch(self.version):
            raise ValueError("tool version must use MAJOR.MINOR.PATCH")
        if not self.description.strip():
            raise ValueError("tool description cannot be blank")
        if not callable(self.handler):
            raise ValueError("tool handler must be callable")
        if self.fallback is not None and not callable(self.fallback):
            raise ValueError("tool fallback must be callable")
        if not self.idempotent and self.policy.retry.max_attempts > 1:
            raise ValueError("non-idempotent tools cannot be retried automatically")


@dataclass(frozen=True)
class ToolResult:
    """Stable result envelope independent of any individual handler."""

    success: bool
    tool_name: str
    tool_version: str
    call_id: str
    attempts: int
    latency_ms: float
    data: Mapping[str, Any] | None = None
    error: ToolErrorInfo | None = None
    cached: bool = False
    fallback_used: bool = False
    upstream_error: ToolErrorInfo | None = None

    def __post_init__(self) -> None:
        if self.success and self.error is not None:
            raise ValueError("successful results cannot carry a terminal error")
        if not self.success and self.error is None:
            raise ValueError("failed results must carry an error")
        if self.cached and self.fallback_used:
            raise ValueError("a result cannot be both cached and fallback-generated")
        if self.attempts < 0:
            raise ValueError("attempts cannot be negative")
        if (
            self.success
            and not self.cached
            and not self.fallback_used
            and self.attempts < 1
        ):
            raise ValueError(
                "successful non-cached results require at least one attempt"
            )
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")

    @classmethod
    def ok(
        cls,
        *,
        data: Mapping[str, Any],
        tool_name: str,
        tool_version: str,
        call_id: str,
        attempts: int,
        latency_ms: float,
        cached: bool = False,
        fallback_used: bool = False,
        upstream_error: ToolErrorInfo | None = None,
    ) -> "ToolResult":
        return cls(
            success=True,
            data=data,
            tool_name=tool_name,
            tool_version=tool_version,
            call_id=call_id,
            attempts=attempts,
            latency_ms=latency_ms,
            cached=cached,
            fallback_used=fallback_used,
            upstream_error=upstream_error,
        )

    @classmethod
    def fail(
        cls,
        *,
        error: ToolErrorInfo,
        tool_name: str,
        tool_version: str,
        call_id: str,
        attempts: int,
        latency_ms: float,
        upstream_error: ToolErrorInfo | None = None,
    ) -> "ToolResult":
        return cls(
            success=False,
            error=error,
            tool_name=tool_name,
            tool_version=tool_version,
            call_id=call_id,
            attempts=attempts,
            latency_ms=latency_ms,
            upstream_error=upstream_error,
        )
