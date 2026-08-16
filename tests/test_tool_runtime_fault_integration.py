from __future__ import annotations

from collections import deque

from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from app.providers.models import ChatResponse, TokenUsage
from app.tools.adapters import build_llm_tools
from app.tools.models import (
    CachePolicy,
    CircuitBreakerPolicy,
    RetryPolicy,
    ToolDefinition,
    ToolPolicy,
)
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


class QueueProvider:
    provider_name = "fake-provider"

    def __init__(self, outcomes):
        self.outcomes = deque(outcomes)
        self.calls = 0

    def chat(self, request):
        self.calls += 1
        outcome = self.outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return ChatResponse(
            content=outcome,
            model="fake-model",
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


def llm_runtime(provider):
    registry = ToolRegistry()
    for definition in build_llm_tools(provider):
        registry.register(definition)
    return ToolRuntime(
        registry,
        sleep=lambda _: None,
        call_id_factory=lambda: "fault-test-call",
    )


def llm_params():
    return {
        "messages": [{"role": "user", "content": "只使用输入事实。"}],
        "temperature": 0.0,
    }


def test_rate_limit_then_success_is_retried_through_real_llm_adapter():
    provider = QueueProvider(
        [
            ProviderRateLimitError(
                provider="fake-provider",
                code="rate_limited",
            ),
            "recovered",
        ]
    )
    runtime = llm_runtime(provider)

    result = runtime.execute("llm.chat", llm_params())

    assert result.success is True
    assert result.data["content"] == "recovered"
    assert result.attempts == 2
    assert provider.calls == 2
    metrics = runtime.metrics.snapshot("llm.chat")
    assert metrics.retries == 1
    assert metrics.upstream_successes == 1


def test_authentication_failure_is_not_retried_and_stays_redacted(capsys):
    secret = "sk-sensitive-key-must-not-leak"
    provider = QueueProvider(
        [
            ProviderAuthenticationError(
                provider="fake-provider",
                code="authentication_failed",
            )
        ]
    )
    runtime = llm_runtime(provider)
    params = {
        "messages": [
            {
                "role": "user",
                "content": f"private prompt containing {secret}",
            }
        ],
        "temperature": 0.0,
    }

    result = runtime.execute("llm.chat", params)
    captured = capsys.readouterr()

    assert result.success is False
    assert result.attempts == 1
    assert provider.calls == 1
    assert result.error.code == "authentication_failed"
    rendered = f"{result.error.message}\n{captured.out}\n{captured.err}"
    assert secret not in rendered
    assert "private prompt" not in rendered


def test_open_circuit_uses_fallback_and_tracks_upstream_failure():
    calls = 0

    def failing_handler(params, context):
        nonlocal calls
        calls += 1
        raise ProviderRateLimitError(
            provider="fake-provider",
            code="rate_limited",
        )

    def fallback(params, context, error):
        return {"status": "deterministic_fallback"}

    definition = ToolDefinition(
        name="report.generate",
        version="1.0.0",
        description="Generate or safely degrade a report.",
        handler=failing_handler,
        fallback=fallback,
        input_schema={
            "type": "object",
            "properties": {"summary_id": {"type": "string"}},
            "required": ["summary_id"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"status": {"type": "string"}},
            "required": ["status"],
            "additionalProperties": False,
        },
        policy=ToolPolicy(
            retry=RetryPolicy(max_attempts=1),
            circuit_breaker=CircuitBreakerPolicy(
                failure_threshold=1,
                recovery_s=30,
            ),
        ),
    )
    registry = ToolRegistry()
    registry.register(definition)
    runtime = ToolRuntime(registry)

    first = runtime.execute("report.generate", {"summary_id": "demo"})
    second = runtime.execute("report.generate", {"summary_id": "demo"})

    assert first.success is True
    assert first.fallback_used is True
    assert first.upstream_error.code == "rate_limited"
    assert second.success is True
    assert second.fallback_used is True
    assert second.attempts == 0
    assert second.upstream_error.code == "circuit_open"
    assert calls == 1


def test_cache_is_not_polluted_by_mutating_a_previous_result():
    calls = 0

    def handler(params, context):
        nonlocal calls
        calls += 1
        return {"profile": {"name": "safe-original"}}

    definition = ToolDefinition(
        name="profile.lookup",
        version="1.0.0",
        description="Return a cached nested profile.",
        handler=handler,
        input_schema={
            "type": "object",
            "properties": {"puuid": {"type": "string"}},
            "required": ["puuid"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"profile": {"type": "object"}},
            "required": ["profile"],
            "additionalProperties": False,
        },
        policy=ToolPolicy(
            cache=CachePolicy(ttl_s=60)
        ),
    )
    registry = ToolRegistry()
    registry.register(definition)
    runtime = ToolRuntime(registry)
    full_puuid = "FULL-PUUID-SHOULD-NOT-APPEAR-IN-ERRORS"

    first = runtime.execute("profile.lookup", {"puuid": full_puuid})
    first.data["profile"]["name"] = "mutated"
    second = runtime.execute("profile.lookup", {"puuid": full_puuid})

    assert second.cached is True
    assert second.data["profile"]["name"] == "safe-original"
    assert calls == 1
    assert full_puuid not in str(second)
