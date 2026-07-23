"""Per-tool three-state circuit breaker."""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable

from .models import CircuitBreakerPolicy


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        policy: CircuitBreakerPolicy,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._policy = policy
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._probe_in_flight = False

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def allow_call(self) -> bool:
        if self._state is CircuitState.CLOSED:
            return True

        if self._state is CircuitState.OPEN:
            assert self._opened_at is not None
            if self._clock() - self._opened_at < self._policy.recovery_s:
                return False
            self._state = CircuitState.HALF_OPEN
            self._probe_in_flight = False

        if self._probe_in_flight:
            return False
        self._probe_in_flight = True
        return True

    def record_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        self._probe_in_flight = False

    def record_failure(self, *, count_toward_threshold: bool = True) -> None:
        if not count_toward_threshold:
            return

        if self._state is CircuitState.HALF_OPEN:
            self._open()
            return

        self._failure_count += 1
        if self._failure_count >= self._policy.failure_threshold:
            self._open()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._failure_count = self._policy.failure_threshold
        self._opened_at = self._clock()
        self._probe_in_flight = False


class CircuitBreakerRegistry:
    """Lazily creates one isolated breaker for each stable tool name."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(
        self,
        tool_name: str,
        policy: CircuitBreakerPolicy,
    ) -> CircuitBreaker:
        breaker = self._breakers.get(tool_name)
        if breaker is None:
            breaker = CircuitBreaker(policy, clock=self._clock)
            self._breakers[tool_name] = breaker
        return breaker

