from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.agent.loop import (
    AgentLoop,
    AgentRunRequest,
    AgentRunStatus,
    AgentStopReason,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)
from app.tools.models import ToolDefinition, ToolPolicy
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


def echo_definition():
    return ToolDefinition(
        name="system.echo",
        version="1.0.0",
        description="Echo a message for agent-loop tests.",
        handler=lambda params, context: {"echo": params["message"]},
        input_schema=ECHO_INPUT,
        output_schema=ECHO_OUTPUT,
        policy=ToolPolicy(),
    )


@dataclass
class ScriptedProvider:
    responses: list[ChatResponse]
    provider_name: str = "fake-agent-provider"
    model_name: str = "fake-agent-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )

    def __post_init__(self):
        self.requests = []

    def chat(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ClockedProvider(ScriptedProvider):
    def __init__(self, responses, *, clock, advances):
        super().__init__(responses=responses)
        self.clock = clock
        self.advances = list(advances)

    def chat(self, request):
        self.requests.append(request)
        self.clock.advance(self.advances.pop(0))
        return self.responses.pop(0)


def build_loop(
    provider,
    *,
    context_sizer=None,
    clock=None,
    tool_definition=None,
):
    registry = ToolRegistry()
    registry.register(tool_definition or echo_definition())
    runtime_kwargs = {"call_id_factory": lambda: "runtime-call"}
    loop_kwargs = {}
    if clock is not None:
        runtime_kwargs["clock"] = clock
        loop_kwargs["clock"] = clock
    if context_sizer is not None:
        loop_kwargs["context_sizer"] = context_sizer
    return AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(registry, **runtime_kwargs),
        **loop_kwargs,
    )


def final_response(content: str) -> ChatResponse:
    return ChatResponse(
        content=content,
        model="fake-agent-model",
        provider="fake-agent-provider",
        usage=TokenUsage(input_tokens=2, output_tokens=3),
    )


def tool_response(name: str = "system.echo", arguments=None) -> ChatResponse:
    return ChatResponse(
        content=None,
        model="fake-agent-model",
        provider="fake-agent-provider",
        tool_calls=(
            ToolCall(
                id="model-call-1",
                name=name,
                arguments=arguments or {"message": "hello"},
            ),
        ),
        usage=TokenUsage(input_tokens=5, output_tokens=4),
    )


def test_agent_loop_executes_tool_then_returns_final_response():
    provider = ScriptedProvider(
        responses=[
            tool_response(),
            final_response("工具结果已收到"),
        ]
    )
    loop = build_loop(provider)

    result = loop.run(
        AgentRunRequest(
            messages=(
                ChatMessage(role=MessageRole.USER, content="请回显 hello"),
            ),
            allowed_tools=("system.echo",),
        )
    )

    assert result.status is AgentRunStatus.COMPLETED
    assert result.stop_reason is AgentStopReason.FINAL_RESPONSE
    assert result.final_response.content == "工具结果已收到"
    assert len(result.tool_executions) == 1
    assert result.tool_executions[0].result.data == {"echo": "hello"}
    assert result.usage.total_tokens == 14
    assert len(provider.requests) == 2
    assert provider.requests[0].tools[0].name == "system.echo"
    assert provider.requests[1].messages[-1].role is MessageRole.TOOL
    assert '"echo":"hello"' in provider.requests[1].messages[-1].content


def test_agent_loop_can_finish_without_tools():
    provider = ScriptedProvider([final_response("直接回答")])
    result = build_loop(provider).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="你好"),)
        )
    )

    assert result.status is AgentRunStatus.COMPLETED
    assert result.stop_reason is AgentStopReason.FINAL_RESPONSE
    assert result.tool_executions == ()
    assert provider.requests[0].tools == ()


def test_agent_run_request_validates_context_ceiling_contract():
    messages = (ChatMessage(role=MessageRole.USER, content="你好"),)

    request = AgentRunRequest(messages=messages)
    assert request.max_context_tokens == 200_000
    assert AgentStopReason.CONTEXT_BUDGET_EXCEEDED.value == (
        "context_budget_exceeded"
    )
    assert AgentStopReason.TIMEOUT.value == "timeout"

    for invalid in (0, -1, True):
        with pytest.raises(ValueError, match="max_context_tokens"):
            AgentRunRequest(
                messages=messages,
                max_context_tokens=invalid,
            )


def test_agent_loop_rejects_tool_outside_allowlist():
    provider = ScriptedProvider([tool_response(name="system.secret")])
    result = build_loop(provider).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
        )
    )

    assert result.status is AgentRunStatus.FAILED
    assert result.stop_reason is AgentStopReason.TOOL_NOT_ALLOWED
    assert result.error_code == "tool_not_allowed"
    assert result.tool_executions == ()


def test_agent_loop_rejects_text_only_provider_before_calling_it():
    provider = ScriptedProvider(
        [tool_response()],
        capabilities=ProviderCapabilities(text_chat=True),
    )
    result = build_loop(provider).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
        )
    )

    assert result.status is AgentRunStatus.FAILED
    assert result.stop_reason is AgentStopReason.PROVIDER_ERROR
    assert result.error_code == "unsupported_capability"
    assert provider.requests == []


def test_agent_loop_stops_at_iteration_budget_before_unbounded_execution():
    provider = ScriptedProvider([tool_response()])
    result = build_loop(provider).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
            max_iterations=1,
        )
    )

    assert result.status is AgentRunStatus.STOPPED
    assert result.stop_reason is AgentStopReason.MAX_ITERATIONS
    assert result.tool_executions == ()


def test_agent_loop_stops_repeated_identical_tool_calls():
    repeated = tool_response()
    provider = ScriptedProvider([repeated, repeated])
    result = build_loop(provider).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
        )
    )

    assert result.status is AgentRunStatus.STOPPED
    assert result.stop_reason is AgentStopReason.DUPLICATE_TOOL_CALL
    assert len(result.tool_executions) == 1


def test_agent_loop_stops_initial_context_overflow_before_provider_call():
    class OversizedSizer:
        def estimate_messages(self, messages):
            return 101

    provider = ScriptedProvider([final_response("must not be called")])
    result = build_loop(
        provider,
        context_sizer=OversizedSizer(),
    ).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="你好"),),
            max_context_tokens=100,
        )
    )

    assert result.status is AgentRunStatus.STOPPED
    assert result.stop_reason is AgentStopReason.CONTEXT_BUDGET_EXCEEDED
    assert result.iterations == 0
    assert provider.requests == []


def test_agent_loop_blocks_second_provider_call_after_observation_overflow():
    class GrowingSizer:
        def __init__(self):
            self.estimates = iter((1, 101))

        def estimate_messages(self, messages):
            return next(self.estimates)

    provider = ScriptedProvider(
        [tool_response(), final_response("must not be called")]
    )
    result = build_loop(
        provider,
        context_sizer=GrowingSizer(),
    ).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
            max_context_tokens=100,
        )
    )

    assert result.status is AgentRunStatus.STOPPED
    assert result.stop_reason is AgentStopReason.CONTEXT_BUDGET_EXCEEDED
    assert result.iterations == 1
    assert len(provider.requests) == 1
    assert len(result.tool_executions) == 1


def test_agent_loop_passes_decreasing_total_deadline_to_provider_and_tool():
    clock = FakeClock()
    tool_remaining: list[float] = []

    def handler(params, context):
        tool_remaining.append(context.remaining_s())
        clock.advance(3)
        return {"echo": params["message"]}

    tool = ToolDefinition(
        name="system.echo",
        version="1.0.0",
        description="Echo with a fake-clock delay.",
        handler=handler,
        input_schema=ECHO_INPUT,
        output_schema=ECHO_OUTPUT,
        policy=ToolPolicy(timeout_s=30),
    )
    provider = ClockedProvider(
        [tool_response(), final_response("done")],
        clock=clock,
        advances=[2, 0],
    )

    result = build_loop(
        provider,
        clock=clock,
        tool_definition=tool,
    ).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
            timeout_s=10,
        )
    )

    assert result.status is AgentRunStatus.COMPLETED
    assert [request.timeout_s for request in provider.requests] == pytest.approx(
        [10, 5]
    )
    assert tool_remaining == pytest.approx([8])


def test_agent_loop_does_not_execute_tool_after_total_deadline():
    clock = FakeClock()
    tool_calls = 0

    def handler(params, context):
        nonlocal tool_calls
        tool_calls += 1
        return {"echo": params["message"]}

    tool = ToolDefinition(
        name="system.echo",
        version="1.0.0",
        description="A tool that must not run after the deadline.",
        handler=handler,
        input_schema=ECHO_INPUT,
        output_schema=ECHO_OUTPUT,
        policy=ToolPolicy(timeout_s=30),
    )
    provider = ClockedProvider(
        [tool_response()],
        clock=clock,
        advances=[11],
    )

    result = build_loop(
        provider,
        clock=clock,
        tool_definition=tool,
    ).run(
        AgentRunRequest(
            messages=(ChatMessage(role=MessageRole.USER, content="执行工具"),),
            allowed_tools=("system.echo",),
            timeout_s=10,
        )
    )

    assert result.status is AgentRunStatus.STOPPED
    assert result.stop_reason is AgentStopReason.TIMEOUT
    assert result.iterations == 1
    assert tool_calls == 0
    assert result.tool_executions == ()
