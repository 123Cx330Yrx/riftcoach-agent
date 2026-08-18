"""Body-free task metrics and structured logging.

The task layer needs enough signals to operate a queue without turning logs
into a second data store.  This module therefore has an explicit metadata
allowlist and never accepts arbitrary exception text, prompts or report
content as an event field.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Mapping


SAFE_METADATA_FIELDS = frozenset(
    {
        "task_id",
        "run_id",
        "worker_id",
        "status",
        "phase",
        "reason",
        "outcome",
        "latency_ms",
        "queue_delay_ms",
        "sample_count",
        "environment",
        "profile",
        "disposition",
        "cleanup_pending",
    }
)
_SAFE_EVENT_NAME = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@|+\-]{0,255}$")
_SENSITIVE_VALUE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|prompt|report|postgres(?:ql)?://|bearer)"
)


@dataclass(frozen=True, slots=True)
class TaskEvent:
    name: str
    metadata: dict[str, str | int | float | bool]


@dataclass(frozen=True, slots=True)
class TaskMetricsSnapshot:
    counters: dict[str, int]
    latencies_ms: dict[str, tuple[float, ...]]

    def public_metadata(self) -> dict[str, tuple[str, ...]]:
        return {
            "counter_names": tuple(sorted(self.counters)),
            "latency_names": tuple(sorted(self.latencies_ms)),
        }


@dataclass(frozen=True, slots=True)
class PercentileResult:
    value_ms: float
    sample_count: int
    target_name: str


class TaskObservability:
    """Thread-safe in-process metrics plus body-free structured events."""

    def __init__(
        self,
        *,
        logger_name: str = "riftcoach.tasks",
        max_events: int = 1_000,
    ) -> None:
        if isinstance(max_events, bool) or not isinstance(max_events, int):
            raise TypeError("max_events must be an integer")
        if max_events < 1:
            raise ValueError("max_events must be greater than zero")
        self._logger = logging.getLogger(logger_name)
        self._max_events = max_events
        self._events: deque[TaskEvent] = deque(maxlen=max_events)
        self._counters: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}
        self._lock = Lock()

    @property
    def events(self) -> tuple[TaskEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def emit(self, name: str, metadata: Mapping[str, Any] | None = None) -> None:
        if not isinstance(name, str) or not name or any(
            character not in _SAFE_EVENT_NAME for character in name
        ):
            raise ValueError("event name must be a bounded safe identifier")
        safe = _sanitize_metadata(metadata or {})
        event = TaskEvent(name=name, metadata=safe)
        with self._lock:
            self._events.append(event)
        # Serialize only the projected envelope.  No ``exc_info`` or stack is
        # passed, by design.
        self._logger.info(
            json.dumps(
                {"event": event.name, **event.metadata},
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    def increment(self, name: str, *, amount: int = 1) -> None:
        _validate_metric_name(name)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def observe_latency(self, name: str, latency_ms: float) -> None:
        _validate_metric_name(name)
        if isinstance(latency_ms, bool) or not isinstance(latency_ms, (int, float)):
            raise TypeError("latency_ms must be a finite number")
        if not math.isfinite(float(latency_ms)) or latency_ms < 0:
            raise ValueError("latency_ms must be a finite non-negative number")
        with self._lock:
            self._latencies.setdefault(name, []).append(float(latency_ms))

    def snapshot(self) -> TaskMetricsSnapshot:
        with self._lock:
            return TaskMetricsSnapshot(
                counters=dict(self._counters),
                latencies_ms={
                    name: tuple(values)
                    for name, values in self._latencies.items()
                },
            )


def percentile(values: list[float] | tuple[float, ...], quantile: float) -> PercentileResult:
    """Return a deterministic nearest-rank percentile with sample metadata."""

    if not values:
        raise ValueError("percentile requires at least one sample")
    if isinstance(quantile, bool) or not isinstance(quantile, (int, float)):
        raise TypeError("quantile must be a number")
    if not math.isfinite(float(quantile)) or not 0 < quantile <= 1:
        raise ValueError("quantile must be in the range (0, 1]")
    normalized: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("percentile samples must be numbers")
        if not math.isfinite(float(value)) or value < 0:
            raise ValueError("percentile samples must be finite and non-negative")
        normalized.append(float(value))
    normalized.sort()
    index = max(0, math.ceil(float(quantile) * len(normalized)) - 1)
    return PercentileResult(
        value_ms=normalized[index],
        sample_count=len(normalized),
        target_name=f"p{int(round(float(quantile) * 100))}",
    )


def _sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, str | int | float | bool]:
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    projected: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if key not in SAFE_METADATA_FIELDS:
            continue
        if isinstance(value, bool):
            projected[key] = value
        elif isinstance(value, int) and not isinstance(value, bool):
            projected[key] = value
        elif isinstance(value, float):
            if math.isfinite(value):
                projected[key] = value
        elif isinstance(value, str) and len(value) <= 256:
            if _SENSITIVE_VALUE.search(value):
                continue
            if _SAFE_VALUE.fullmatch(value):
                projected[key] = value
    return projected


def _validate_metric_name(name: str) -> None:
    if not isinstance(name, str) or not name or any(
        character not in _SAFE_EVENT_NAME for character in name
    ):
        raise ValueError("metric name must be a bounded safe identifier")


__all__ = [
    "PercentileResult",
    "SAFE_METADATA_FIELDS",
    "TaskEvent",
    "TaskMetricsSnapshot",
    "TaskObservability",
    "percentile",
]
