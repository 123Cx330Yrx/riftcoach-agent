from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.agent.loop import AgentLoop, AgentRunRequest, AgentRunStatus, AgentStopReason
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderResponseError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.observer import RuntimeObservationError
from app.runtime.signals import (
    AgentRunTerminatedSignal,
    ProviderCallCompletedSignal,
    ProviderCallFailedSignal,
    ProviderCallStartedSignal,
    RuntimeAgentStatus,
    RuntimeAgentStopReason,
    ToolCallCompletedSignal,
    ToolCallStartedSignal,
)
from app.tools.models import (
    ToolDefinition,
    ToolErrorInfo,
    ToolPolicy,
    ToolResult,
)
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


ECHO_INPUT = {
    "type": "object",
    "properties": {"message": {"type": "string", "minLength": 1}},
    "required": ["message"],
    "additionalProperties": False,
}
ECHO_OUTPUT = {
    "type": "object",
    "properties": {"echo": {"type": "string"}},
    "required": ["echo"],
    "additionalProperties": False,
}


class RecordingObserver:
    def __init__(self) -> None:
        self.signals = []

    def observe(self, signal) -> None:
        self.signals.append(signal)


class SelectiveFailingObserver(RecordingObserver):
    def __init__(self, signal_type: type) -> None:
        super().__init__()
        self.signal_type = signal_type

    def observe(self, signal) -> None:
        if isinstance(signal, self.signal_type):
            raise RuntimeError("private observer failure")
        super().observe(signal)


@dataclass
class ScriptedProvider:
    outcomes: list[ChatResponse | Exception]
    provider_name: str = "fake-agent-provider"
    model_name: str = "fake-agent-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )

    def __post_init__(self) -> None:
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class AdvancingProvider(ScriptedProvider):
    def __init__(self, outcomes, *, clock: FakeClock, advance_s: float) -> None:
        super().__init__(outcomes=outcomes)
        self.clock = clock
        self.advance_s = advance_s

    def chat(self, request: ChatRequest) -> ChatResponse:
        response = super().chat(request)
        self.clock.advance(self.advance_s)
        return response


class ScriptedToolRuntime:
    def __init__(self, results: list[ToolResult]) -> None:
        self.results = results
        self.calls = []

    def execute(self, tool_name, params, **kwargs) -> ToolResult:
        self.calls.append((tool_name, params, kwargs))
        return self.results.pop(0)


def _tool_definition(*, handler=None) -> ToolDefinition:
    return ToolDefinition(
        name="system.echo",
        version="1.0.0",
        description="Echo a message.",
        handler=handler or (lambda params, context: {"echo": params["message"]}),
        input_schema=ECHO_INPUT,
        output_schema=ECHO_OUTPUT,
        policy=ToolPolicy(),
    )


def _final_response(content: str = "done") -> ChatResponse:
    return ChatResponse(
        content=content,
        model="fake-agent-model",
        provider="fake-agent-provider",
        usage=TokenUsage(input_tokens=2, output_tokens=3),
        finish_reason="stop",
    )


def _tool_response(*calls: ToolCall) -> ChatResponse:
    tool_calls = calls or (
        ToolCall(
            id="model-call-1",
            name="system.echo",
            arguments={"message": "hello"},
        ),
    )
    return ChatResponse(
        content=None,
        model="fake-agent-model",
        provider="fake-agent-provider",
        usage=TokenUsage(input_tokens=5, output_tokens=4),
        tool_calls=tool_calls,
        finish_reason="tool_calls",
    )


def _build_loop(
    delegate,
    observer,
    *,
    tool_runtime=None,
    tool_definition=None,
    context_sizer=None,
    clock=None,
    register_tool: bool = True,
) -> AgentLoop:
    registry = ToolRegistry()
    if register_tool:
        registry.register(tool_definition or _tool_definition())
    runtime = tool_runtime or ToolRuntime(
        registry,
        call_id_factory=lambda: "private-runtime-call-id",
        **({"clock": clock} if clock is not None else {}),
    )
    return AgentLoop(
        provider=ObservedLLMProvider(delegate=delegate, observer=observer),
        tool_registry=registry,
        tool_runtime=runtime,
        **({"context_sizer": context_sizer} if context_sizer is not None else {}),
        **({"clock": clock} if clock is not None else {}),
    )


def _request(**kwargs) -> AgentRunRequest:
    return AgentRunRequest(
        messages=(ChatMessage(role=MessageRole.USER, content="private user text"),),
        allowed_tools=("system.echo",),
        **kwargs,
    )


def _terminal_signals(observer) -> list[AgentRunTerminatedSignal]:
    return [
        signal
        for signal in observer.signals
        if isinstance(signal, AgentRunTerminatedSignal)
    ]


def test_agent_observation_follows_real_provider_tool_and_terminal_order():
    delegate = ScriptedProvider([_tool_response(), _final_response()])
    observer = RecordingObserver()
    result = _build_loop(delegate, observer).run(_request(), observer=observer)

    assert result.status is AgentRunStatus.COMPLETED
    assert [type(signal) for signal in observer.signals] == [
        ProviderCallStartedSignal,
        ProviderCallCompletedSignal,
        ToolCallStartedSignal,
        ToolCallCompletedSignal,
        ProviderCallStartedSignal,
        ProviderCallCompletedSignal,
        AgentRunTerminatedSignal,
    ]
    tool_started = observer.signals[2]
    tool_completed = observer.signals[3]
    terminal = observer.signals[-1]
    assert tool_started.ordinal == tool_completed.ordinal == 1
    assert tool_started.iteration == 1
    assert tool_completed.model_dump() == {
        "kind": "tool_call_completed",
        "tool_name": "system.echo",
        "tool_version": "1.0.0",
        "ordinal": 1,
        "success": True,
        "failure_code": None,
        "attempts": 1,
        "latency_ms": tool_completed.latency_ms,
        "cached": False,
        "fallback_used": False,
    }
    assert terminal.status is RuntimeAgentStatus.COMPLETED
    assert terminal.stop_reason is RuntimeAgentStopReason.FINAL_RESPONSE
    assert terminal.iterations == 2
    assert terminal.error_code is None


@pytest.mark.parametrize(
    ("tool_result", "expected"),
    [
        (
            ToolResult.ok(
                data={"echo": "cached private data"},
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="private-cache-call-id",
                attempts=0,
                latency_ms=1.25,
                cached=True,
            ),
            (True, None, 0, 1.25, True, False),
        ),
        (
            ToolResult.ok(
                data={"echo": "fallback private data"},
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="private-fallback-call-id",
                attempts=2,
                latency_ms=3.5,
                fallback_used=True,
                upstream_error=ToolErrorInfo(
                    code="private_upstream_code",
                    message="private upstream message",
                ),
            ),
            (True, None, 2, 3.5, False, True),
        ),
        (
            ToolResult.fail(
                error=ToolErrorInfo(
                    code="invalid_tool_input",
                    message="private validation detail",
                ),
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="private-failure-call-id",
                attempts=0,
                latency_ms=2.0,
            ),
            (False, "invalid_tool_input", 0, 2.0, False, False),
        ),
        (
            ToolResult.fail(
                error=ToolErrorInfo(
                    code="private_but_safe_looking_tool_code",
                    message="private tool failure",
                ),
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="private-unknown-call-id",
                attempts=1,
                latency_ms=4.0,
            ),
            (False, "tool_failed", 1, 4.0, False, False),
        ),
    ],
)
def test_tool_completion_projects_only_safe_result_envelope(tool_result, expected):
    delegate = ScriptedProvider([_tool_response(), _final_response()])
    observer = RecordingObserver()
    runtime = ScriptedToolRuntime([tool_result])

    _build_loop(delegate, observer, tool_runtime=runtime).run(
        _request(),
        observer=observer,
    )

    completed = next(
        signal
        for signal in observer.signals
        if isinstance(signal, ToolCallCompletedSignal)
    )
    assert (
        completed.success,
        completed.failure_code,
        completed.attempts,
        completed.latency_ms,
        completed.cached,
        completed.fallback_used,
    ) == expected
    serialized = completed.model_dump_json()
    for forbidden in (
        "private data",
        "private upstream",
        "private validation",
        "private tool failure",
        "private-cache-call-id",
        "private-fallback-call-id",
        "private-failure-call-id",
        "private-unknown-call-id",
        "arguments",
        "data",
        "call_id",
        "error",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("response", "request_overrides", "expected_status", "expected_reason"),
    [
        (
            _tool_response(
                ToolCall(id="a", name="system.echo", arguments={"message": "one"}),
                ToolCall(id="b", name="system.echo", arguments={"message": "two"}),
            ),
            {"max_tool_calls": 1},
            RuntimeAgentStatus.STOPPED,
            RuntimeAgentStopReason.MAX_TOOL_CALLS,
        ),
        (
            _tool_response(
                ToolCall(id="a", name="system.echo", arguments={"message": "ok"}),
                ToolCall(id="b", name="system.secret", arguments={"message": "no"}),
            ),
            {},
            RuntimeAgentStatus.FAILED,
            RuntimeAgentStopReason.TOOL_NOT_ALLOWED,
        ),
        (
            _tool_response(
                ToolCall(id="a", name="system.echo", arguments={"message": "same"}),
                ToolCall(id="b", name="system.echo", arguments={"message": "same"}),
            ),
            {},
            RuntimeAgentStatus.STOPPED,
            RuntimeAgentStopReason.DUPLICATE_TOOL_CALL,
        ),
    ],
)
def test_batch_preflight_failure_emits_no_tool_started(
    response,
    request_overrides,
    expected_status,
    expected_reason,
):
    delegate = ScriptedProvider([response])
    observer = RecordingObserver()

    _build_loop(delegate, observer).run(
        _request(**request_overrides),
        observer=observer,
    )

    assert not any(
        isinstance(signal, ToolCallStartedSignal) for signal in observer.signals
    )
    terminals = _terminal_signals(observer)
    assert len(terminals) == 1
    assert terminals[0].status is expected_status
    assert terminals[0].stop_reason is expected_reason


def test_tool_started_observation_failure_prevents_tool_execution():
    handler_calls = 0

    def handler(params, context):
        nonlocal handler_calls
        handler_calls += 1
        return {"echo": params["message"]}

    delegate = ScriptedProvider([_tool_response()])
    observer = SelectiveFailingObserver(ToolCallStartedSignal)
    loop = _build_loop(
        delegate,
        observer,
        tool_definition=_tool_definition(handler=handler),
    )

    with pytest.raises(RuntimeObservationError):
        loop.run(_request(), observer=observer)

    assert handler_calls == 0
    assert len(delegate.requests) == 1


def test_tool_completed_observation_failure_stops_before_next_provider_call():
    handler_calls = 0

    def handler(params, context):
        nonlocal handler_calls
        handler_calls += 1
        return {"echo": params["message"]}

    delegate = ScriptedProvider([_tool_response(), _final_response()])
    observer = SelectiveFailingObserver(ToolCallCompletedSignal)
    loop = _build_loop(
        delegate,
        observer,
        tool_definition=_tool_definition(handler=handler),
    )

    with pytest.raises(RuntimeObservationError):
        loop.run(_request(), observer=observer)

    assert handler_calls == 1
    assert len(delegate.requests) == 1


def test_agent_terminal_observation_failure_does_not_return_unobserved_result():
    delegate = ScriptedProvider([_final_response()])
    observer = SelectiveFailingObserver(AgentRunTerminatedSignal)
    loop = _build_loop(delegate, observer)

    with pytest.raises(RuntimeObservationError):
        loop.run(_request(), observer=observer)

    assert len(delegate.requests) == 1
    assert not _terminal_signals(observer)


def test_provider_failure_closes_provider_and_agent_lifecycles_safely():
    delegate = ScriptedProvider(
        [ProviderResponseError(provider="fake-agent-provider", code="private_detail")]
    )
    observer = RecordingObserver()
    result = _build_loop(delegate, observer).run(_request(), observer=observer)

    assert result.status is AgentRunStatus.FAILED
    assert result.stop_reason is AgentStopReason.PROVIDER_ERROR
    assert [type(signal) for signal in observer.signals] == [
        ProviderCallStartedSignal,
        ProviderCallFailedSignal,
        AgentRunTerminatedSignal,
    ]
    failed = observer.signals[1]
    terminal = observer.signals[2]
    assert failed.failure_code == "provider_failed"
    assert failed.provider_error_code is None
    assert terminal.error_code == "provider_failed"
    assert "private_detail" not in terminal.model_dump_json()


def test_capability_preflight_failure_has_no_provider_signal_but_has_agent_terminal():
    delegate = ScriptedProvider(
        [_tool_response()],
        capabilities=ProviderCapabilities(text_chat=True),
    )
    observer = RecordingObserver()
    result = _build_loop(delegate, observer).run(_request(), observer=observer)

    assert result.status is AgentRunStatus.FAILED
    assert delegate.requests == []
    assert not any(
        isinstance(signal, ProviderCallStartedSignal) for signal in observer.signals
    )
    terminal = _terminal_signals(observer)
    assert len(terminal) == 1
    assert terminal[0].stop_reason is RuntimeAgentStopReason.PROVIDER_ERROR
    assert terminal[0].error_code == "provider_failed"


def test_context_budget_max_iteration_timeout_and_invalid_tool_have_terminals():
    class OversizedSizer:
        def estimate_messages(self, messages):
            return 101

    context_observer = RecordingObserver()
    context_provider = ScriptedProvider([_final_response()])
    context_result = _build_loop(
        context_provider,
        context_observer,
        context_sizer=OversizedSizer(),
    ).run(_request(max_context_tokens=100), observer=context_observer)

    iteration_observer = RecordingObserver()
    iteration_provider = ScriptedProvider([_tool_response()])
    iteration_result = _build_loop(iteration_provider, iteration_observer).run(
        _request(max_iterations=1),
        observer=iteration_observer,
    )

    clock = FakeClock()
    timeout_observer = RecordingObserver()
    timeout_provider = AdvancingProvider(
        [_tool_response()],
        clock=clock,
        advance_s=2,
    )
    timeout_result = _build_loop(
        timeout_provider,
        timeout_observer,
        clock=clock,
    ).run(_request(timeout_s=1), observer=timeout_observer)

    invalid_observer = RecordingObserver()
    invalid_provider = ScriptedProvider([_final_response()])
    invalid_result = _build_loop(
        invalid_provider,
        invalid_observer,
        register_tool=False,
    ).run(_request(), observer=invalid_observer)

    assert (
        context_result.stop_reason,
        _terminal_signals(context_observer)[0].stop_reason,
    ) == (
        AgentStopReason.CONTEXT_BUDGET_EXCEEDED,
        RuntimeAgentStopReason.CONTEXT_BUDGET_EXCEEDED,
    )
    assert (
        iteration_result.stop_reason,
        _terminal_signals(iteration_observer)[0].stop_reason,
    ) == (
        AgentStopReason.MAX_ITERATIONS,
        RuntimeAgentStopReason.MAX_ITERATIONS,
    )
    assert (
        timeout_result.stop_reason,
        _terminal_signals(timeout_observer)[0].stop_reason,
    ) == (AgentStopReason.TIMEOUT, RuntimeAgentStopReason.TIMEOUT)
    invalid_terminal = _terminal_signals(invalid_observer)
    assert invalid_result.stop_reason is AgentStopReason.INVALID_TOOL_CONFIGURATION
    assert len(invalid_terminal) == 1
    assert (
        invalid_terminal[0].status,
        invalid_terminal[0].stop_reason,
        invalid_terminal[0].error_code,
    ) == (
        RuntimeAgentStatus.FAILED,
        RuntimeAgentStopReason.INVALID_TOOL_CONFIGURATION,
        "tool_not_found",
    )


def test_observer_none_preserves_legacy_result_and_provider_calls_exactly():
    clock_a = FakeClock()
    clock_b = FakeClock()
    provider_a = ScriptedProvider([_final_response("same")])
    provider_b = ScriptedProvider([_final_response("same")])
    registry_a = ToolRegistry()
    registry_b = ToolRegistry()
    loop_a = AgentLoop(
        provider=provider_a,
        tool_registry=registry_a,
        tool_runtime=ToolRuntime(registry_a, clock=clock_a),
        clock=clock_a,
    )
    loop_b = AgentLoop(
        provider=provider_b,
        tool_registry=registry_b,
        tool_runtime=ToolRuntime(registry_b, clock=clock_b),
        clock=clock_b,
    )
    request = AgentRunRequest(
        messages=(ChatMessage(role=MessageRole.USER, content="same"),)
    )

    legacy = loop_a.run(request)
    closed_port = loop_b.run(request, observer=None)

    assert closed_port == legacy
    assert provider_b.requests == provider_a.requests
