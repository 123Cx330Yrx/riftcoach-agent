from app.tools.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
)
from app.tools.models import CircuitBreakerPolicy


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_breaker(clock: FakeClock) -> CircuitBreaker:
    return CircuitBreaker(
        CircuitBreakerPolicy(failure_threshold=2, recovery_s=10),
        clock=clock,
    )


def test_closed_breaker_opens_after_counted_failures():
    clock = FakeClock()
    breaker = make_breaker(clock)

    assert breaker.state is CircuitState.CLOSED
    assert breaker.allow_call() is True
    breaker.record_failure(count_toward_threshold=True)
    assert breaker.state is CircuitState.CLOSED

    breaker.record_failure(count_toward_threshold=True)

    assert breaker.state is CircuitState.OPEN
    assert breaker.allow_call() is False


def test_non_retryable_caller_failures_do_not_open_breaker():
    clock = FakeClock()
    breaker = make_breaker(clock)

    for _ in range(10):
        breaker.record_failure(count_toward_threshold=False)

    assert breaker.state is CircuitState.CLOSED
    assert breaker.failure_count == 0
    assert breaker.allow_call() is True


def test_open_breaker_allows_exactly_one_half_open_probe():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()

    clock.advance(9.9)
    assert breaker.allow_call() is False

    clock.advance(0.2)
    assert breaker.allow_call() is True
    assert breaker.state is CircuitState.HALF_OPEN
    assert breaker.allow_call() is False


def test_successful_half_open_probe_closes_breaker():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(10)
    assert breaker.allow_call() is True

    breaker.record_success()

    assert breaker.state is CircuitState.CLOSED
    assert breaker.failure_count == 0
    assert breaker.allow_call() is True


def test_failed_half_open_probe_reopens_and_restarts_recovery_window():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(10)
    assert breaker.allow_call() is True

    breaker.record_failure()

    assert breaker.state is CircuitState.OPEN
    clock.advance(9.9)
    assert breaker.allow_call() is False
    clock.advance(0.2)
    assert breaker.allow_call() is True


def test_success_in_closed_state_resets_accumulated_failures():
    clock = FakeClock()
    breaker = make_breaker(clock)
    breaker.record_failure()

    breaker.record_success()

    assert breaker.failure_count == 0
    assert breaker.state is CircuitState.CLOSED


def test_registry_keeps_independent_breakers_per_tool():
    clock = FakeClock()
    registry = CircuitBreakerRegistry(clock=clock)
    policy = CircuitBreakerPolicy(failure_threshold=1, recovery_s=10)

    first = registry.get("riot.recent_matches", policy)
    same = registry.get("riot.recent_matches", policy)
    other = registry.get("rag.search", policy)

    assert first is same
    assert first is not other
    first.record_failure()
    assert first.state is CircuitState.OPEN
    assert other.state is CircuitState.CLOSED

