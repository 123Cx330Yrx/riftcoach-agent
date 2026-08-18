"""Small, clock-injectable data-retention contracts for the task base.

Retention is intentionally independent from the Agent/Provider runtime.  A
record is expired because of its data class and timestamp, never because a
model run happened to fail or because a process restarted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Callable


class RetentionKind(StrEnum):
    RIOT_CACHE = "riot_cache"
    TERMINAL_RUN = "terminal_run"
    OPERATIONS_LOG = "operations_log"


Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """The frozen 6A defaults, expressed in days for configuration clarity."""

    riot_cache_days: int = 7
    terminal_run_days: int = 90
    operations_log_days: int = 30

    def __post_init__(self) -> None:
        for name, value in (
            ("riot_cache_days", self.riot_cache_days),
            ("terminal_run_days", self.terminal_run_days),
            ("operations_log_days", self.operations_log_days),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")

    def ttl_for(self, kind: RetentionKind) -> timedelta:
        if not isinstance(kind, RetentionKind):
            raise TypeError("kind must be a RetentionKind")
        days = {
            RetentionKind.RIOT_CACHE: self.riot_cache_days,
            RetentionKind.TERMINAL_RUN: self.terminal_run_days,
            RetentionKind.OPERATIONS_LOG: self.operations_log_days,
        }[kind]
        return timedelta(days=days)


@dataclass(frozen=True, slots=True)
class RetentionService:
    policy: RetentionPolicy = RetentionPolicy()
    clock: Clock = lambda: datetime.now(timezone.utc)

    def __post_init__(self) -> None:
        if not isinstance(self.policy, RetentionPolicy):
            raise TypeError("policy must be a RetentionPolicy")
        if not callable(self.clock):
            raise TypeError("clock must be callable")

    def expiry_for(
        self,
        *,
        kind: RetentionKind,
        created_at: datetime,
    ) -> datetime:
        normalized = _as_utc(created_at)
        return normalized + self.policy.ttl_for(kind)

    def is_expired(
        self,
        *,
        kind: RetentionKind,
        created_at: datetime,
        now: datetime | None = None,
    ) -> bool:
        current = _as_utc(self.clock() if now is None else now)
        return current >= self.expiry_for(kind=kind, created_at=created_at)


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    normalized = value.astimezone(timezone.utc)
    if not all(math.isfinite(part) for part in (normalized.timestamp(),)):
        raise ValueError("timestamp must be finite")
    return normalized


__all__ = ["RetentionKind", "RetentionPolicy", "RetentionService"]
