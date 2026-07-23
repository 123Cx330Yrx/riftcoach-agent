"""In-process counters for distinguishing tool execution outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ToolMetricsSnapshot:
    calls: int = 0
    upstream_successes: int = 0
    cache_hits: int = 0
    fallback_successes: int = 0
    failures: int = 0
    retries: int = 0
    circuit_rejections: int = 0
    total_latency_ms: float = 0.0


@dataclass
class _MutableToolMetrics:
    calls: int = 0
    upstream_successes: int = 0
    cache_hits: int = 0
    fallback_successes: int = 0
    failures: int = 0
    retries: int = 0
    circuit_rejections: int = 0
    total_latency_ms: float = 0.0


class ToolMetrics:
    def __init__(self) -> None:
        self._values: dict[str, _MutableToolMetrics] = {}
        self._lock = Lock()

    def increment(self, tool_name: str, field_name: str, amount: int = 1) -> None:
        with self._lock:
            value = self._values.setdefault(tool_name, _MutableToolMetrics())
            if not hasattr(value, field_name) or field_name == "total_latency_ms":
                raise ValueError(f"unknown integer metric: {field_name}")
            setattr(value, field_name, getattr(value, field_name) + amount)

    def observe_latency(self, tool_name: str, latency_ms: float) -> None:
        if latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")
        with self._lock:
            value = self._values.setdefault(tool_name, _MutableToolMetrics())
            value.total_latency_ms += latency_ms

    def snapshot(self, tool_name: str) -> ToolMetricsSnapshot:
        with self._lock:
            value = self._values.get(tool_name)
            if value is None:
                return ToolMetricsSnapshot()
            return ToolMetricsSnapshot(
                calls=value.calls,
                upstream_successes=value.upstream_successes,
                cache_hits=value.cache_hits,
                fallback_successes=value.fallback_successes,
                failures=value.failures,
                retries=value.retries,
                circuit_rejections=value.circuit_rejections,
                total_latency_ms=value.total_latency_ms,
            )

