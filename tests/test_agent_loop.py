from __future__ import annotations

from dataclasses import dataclass

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


def build_loop(provider):
    registry = ToolRegistry()
    registry.register(echo_definition())
    return AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(
            registry,
            call_id_factory=lambda: "runtime-call",
        ),
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
