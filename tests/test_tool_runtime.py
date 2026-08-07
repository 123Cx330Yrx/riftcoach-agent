from __future__ import annotations

from collections import deque

from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from app.tools.circuit_breaker import CircuitState
from app.tools.metrics import ToolMetrics
from app.tools.models import (
    CachePolicy,
    CircuitBreakerPolicy,
    RetryPolicy,
    ToolDefinition,
    ToolPolicy,
)
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


INPUT_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string", "minLength": 1}},
    "required": ["message"],
    "additionalProperties": False,
}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"echo": {"type": "string"}},
    "required": ["echo"],
    "additionalProperties": False,
}


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSleep:
    def __init__(self, clock: FakeClock):
        self.clock = clock
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)
        self.clock.advance(seconds)


def definition(handler, **overrides) -> ToolDefinition:
    values = {
        "name": "system.echo",
        "version": "1.0.0",
        "description": "Echo a test message.",
        "handler": handler,
        "input_schema": INPUT_SCHEMA,
        "output_schema": OUTPUT_SCHEMA,
    }
    values.update(overrides)
    return ToolDefinition(**values)


def runtime_with(
    tool: ToolDefinition | None,
    *,
    clock: FakeClock | None = None,
    sleep=None,
) -> ToolRuntime:
    registry = ToolRegistry()
    if tool is not None:
        registry.register(tool)
    actual_clock = clock or FakeClock()
    return ToolRuntime(
        registry,
        clock=actual_clock,
        sleep=sleep or (lambda _: None),
        call_id_factory=lambda: "call-test",
    )


def test_success_validates_input_and_output_and_records_metrics():
    seen = {}

    def handler(params, context):
        seen["params"] = params
        seen["context"] = context
        return {"echo": params["message"]}

    runtime = runtime_with(definition(handler))

    result = runtime.execute("system.echo", {"message": "hello"})

    assert result.success is True
    assert result.data == {"echo": "hello"}
    assert result.call_id == "call-test"
    assert result.attempts == 1
    assert result.cached is False
    assert result.fallback_used is False
    assert seen["params"] == {"message": "hello"}
    assert seen["context"].attempt == 1
    assert seen["context"].remaining_s(now_monotonic=100.0) == 30.0
    snapshot = runtime.metrics.snapshot("system.echo")
    assert snapshot.calls == 1
    assert snapshot.upstream_successes == 1
    assert snapshot.failures == 0


def test_run_timeout_cap_and_tool_policy_use_the_smaller_deadline():
    clock = FakeClock()
    remaining: list[float] = []

    def handler(params, context):
        remaining.append(context.remaining_s())
        return {"echo": params["message"]}

    tool = definition(handler, policy=ToolPolicy(timeout_s=4))
    runtime = runtime_with(tool, clock=clock)

    first = runtime.execute(
        tool.name,
        {"message": "run cap"},
        timeout_cap_s=2,
    )
    second = runtime.execute(
        tool.name,
        {"message": "tool cap"},
        timeout_cap_s=10,
    )

    assert first.success is True
    assert second.success is True
    assert remaining == [2, 4]


def test_unknown_tool_returns_safe_failure_without_handler_attempt():
    runtime = runtime_with(None)

    result = runtime.execute("missing.tool", {"secret": "must-not-leak"})

    assert result.success is False
    assert result.attempts == 0
    assert result.error.code == "tool_not_found"
    assert "must-not-leak" not in result.error.message


def test_invalid_input_returns_failure_before_handler_and_breaker():
    calls = 0

    def handler(params, context):
        nonlocal calls
        calls += 1
        return {"echo": "never"}

    runtime = runtime_with(definition(handler))

    result = runtime.execute("system.echo", {"message": ""})

    assert result.success is False
    assert result.attempts == 0
    assert result.error.code == "invalid_tool_input"
    assert calls == 0
    assert runtime.breakers.get(
        "system.echo",
        CircuitBreakerPolicy(),
    ).state is CircuitState.CLOSED


def test_invalid_output_is_not_retried_and_does_not_open_breaker():
    calls = 0

    def handler(params, context):
        nonlocal calls
        calls += 1
        return {"wrong": "shape"}

    tool = definition(
        handler,
        policy=ToolPolicy(
            retry=RetryPolicy(max_attempts=3),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_s=10,
            ),
        ),
    )
    runtime = runtime_with(tool)

    result = runtime.execute("system.echo", {"message": "hello"})

    assert result.success is False
    assert result.error.code == "invalid_tool_output"
    assert result.attempts == 1
    assert calls == 1
    assert runtime.breakers.get(
        tool.name, tool.policy.circuit_breaker
    ).state is CircuitState.CLOSED


def test_retryable_error_retries_with_exponential_backoff():
    clock = FakeClock()
    sleep = FakeSleep(clock)
    outcomes = deque(
        [
            ProviderRateLimitError(provider="zhipu", code="rate_limited"),
            ProviderRateLimitError(provider="zhipu", code="rate_limited"),
            {"echo": "recovered"},
        ]
    )

    def handler(params, context):
        outcome = outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    tool = definition(
        handler,
        policy=ToolPolicy(
            timeout_s=10,
            retry=RetryPolicy(
                max_attempts=3,
                base_delay_s=0.5,
                max_delay_s=2,
            ),
        ),
    )
    runtime = runtime_with(tool, clock=clock, sleep=sleep)

    result = runtime.execute(tool.name, {"message": "hello"})

    assert result.success is True
    assert result.attempts == 3
    assert sleep.delays == [0.5, 1.0]
    snapshot = runtime.metrics.snapshot(tool.name)
    assert snapshot.retries == 2
    assert snapshot.upstream_successes == 1


def test_non_retryable_authentication_error_is_not_retried_or_counted():
    calls = 0

    def handler(params, context):
        nonlocal calls
        calls += 1
        raise ProviderAuthenticationError(
            provider="zhipu",
            code="authentication_failed",
        )

    tool = definition(
        handler,
        policy=ToolPolicy(
            retry=RetryPolicy(
                max_attempts=3,
                base_delay_s=0.1,
                max_delay_s=0.2,
            ),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_s=10,
            ),
        ),
    )
    runtime = runtime_with(tool)

    result = runtime.execute(tool.name, {"message": "hello"})

    assert result.success is False
    assert result.attempts == 1
    assert result.error.code == "authentication_failed"
    assert calls == 1
    assert runtime.breakers.get(
        tool.name, tool.policy.circuit_breaker
    ).state is CircuitState.CLOSED


def test_retry_stops_when_remaining_budget_cannot_cover_delay():
    clock = FakeClock()
    sleep = FakeSleep(clock)
    calls = 0

    def handler(params, context):
        nonlocal calls
        calls += 1
        raise ProviderRateLimitError(
            provider="zhipu",
            code="rate_limited",
        )

    tool = definition(
        handler,
        policy=ToolPolicy(
            timeout_s=0.4,
            retry=RetryPolicy(
                max_attempts=3,
                base_delay_s=0.5,
                max_delay_s=1,
            ),
        ),
    )
    runtime = runtime_with(tool, clock=clock, sleep=sleep)

    result = runtime.execute(tool.name, {"message": "hello"})

    assert result.success is False
    assert result.attempts == 1
    assert result.error.code == "retry_budget_exhausted"
    assert calls == 1
    assert sleep.delays == []


def test_cache_hit_skips_handler_and_is_reported_separately():
    calls = 0

    def handler(params, context):
        nonlocal calls
        calls += 1
        return {"echo": params["message"]}

    tool = definition(
        handler,
        policy=ToolPolicy(cache=CachePolicy(ttl_s=30)),
    )
    runtime = runtime_with(tool)

    first = runtime.execute(tool.name, {"message": "hello"})
    second = runtime.execute(tool.name, {"message": "hello"})

    assert first.success is True
    assert first.cached is False
    assert second.success is True
    assert second.cached is True
    assert second.attempts == 0
    assert calls == 1
    snapshot = runtime.metrics.snapshot(tool.name)
    assert snapshot.calls == 2
    assert snapshot.upstream_successes == 1
    assert snapshot.cache_hits == 1


def test_open_circuit_uses_fallback_without_calling_handler():
    handler_calls = 0
    fallback_calls = 0

    def handler(params, context):
        nonlocal handler_calls
        handler_calls += 1
        raise ProviderRateLimitError(
            provider="zhipu",
            code="rate_limited",
        )

    def fallback(params, context, error):
        nonlocal fallback_calls
        fallback_calls += 1
        return {"echo": "degraded"}

    tool = definition(
        handler,
        fallback=fallback,
        policy=ToolPolicy(
            retry=RetryPolicy(max_attempts=1),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_s=10,
            ),
        ),
    )
    runtime = runtime_with(tool)

    first = runtime.execute(tool.name, {"message": "hello"})
    second = runtime.execute(tool.name, {"message": "hello"})

    assert first.success is True
    assert first.fallback_used is True
    assert first.attempts == 1
    assert first.upstream_error.code == "rate_limited"
    assert second.success is True
    assert second.fallback_used is True
    assert second.attempts == 0
    assert second.upstream_error.code == "circuit_open"
    assert handler_calls == 1
    assert fallback_calls == 2
    snapshot = runtime.metrics.snapshot(tool.name)
    assert snapshot.fallback_successes == 2
    assert snapshot.circuit_rejections == 1


def test_failed_fallback_returns_terminal_failure():
    def handler(params, context):
        raise ProviderRateLimitError(
            provider="zhipu",
            code="rate_limited",
        )

    def fallback(params, context, error):
        raise RuntimeError("fallback internal detail")

    tool = definition(handler, fallback=fallback)
    runtime = runtime_with(tool)

    result = runtime.execute(tool.name, {"message": "hello"})

    assert result.success is False
    assert result.error.code == "fallback_failed"
    assert result.upstream_error.code == "rate_limited"
    assert "fallback internal detail" not in result.error.message


def test_metrics_returns_zero_snapshot_for_unseen_tool():
    metrics = ToolMetrics()

    snapshot = metrics.snapshot("never.called")

    assert snapshot.calls == 0
    assert snapshot.failures == 0
    assert snapshot.total_latency_ms == 0
