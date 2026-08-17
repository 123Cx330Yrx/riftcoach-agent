from __future__ import annotations

from dataclasses import dataclass

from app.agent.loop import AgentLoop, AgentRunRequest
from app.evaluation.pi_runtime import (
    PiAllowedTool,
    PiInputMessage,
    PiScriptedAssistantStep,
    PiScriptedToolCall,
    PiScriptedUsage,
    PiSpikePolicy,
    PiSpikeRunRequest,
    PiSidecarController,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)
from app.tools.models import RetryPolicy, ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


KNOWLEDGE_INPUT = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
    },
    "required": ["query", "top_k"],
    "additionalProperties": False,
}
KNOWLEDGE_OUTPUT = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}
SYSTEM_PROMPT = "Use only the declared coaching knowledge tool."
USER_MESSAGE = "Review the frozen recent-form context."
TOOL_ARGUMENTS = {"query": "lane deaths", "top_k": 1}


@dataclass
class ScriptedPythonProvider:
    responses: list[ChatResponse]
    provider_name: str = "riftcoach-scripted"
    model_name: str = "riftcoach-scripted-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )

    def chat(self, _request):
        return self.responses.pop(0)


def _knowledge_runtime():
    calls: list[dict] = []

    def search(params, _context):
        calls.append(dict(params))
        return {"answer": params["query"]}

    definition = ToolDefinition(
        name="knowledge.search",
        version="2.0.0",
        description="Search attributable coaching knowledge.",
        handler=search,
        input_schema=KNOWLEDGE_INPUT,
        output_schema=KNOWLEDGE_OUTPUT,
        policy=ToolPolicy(retry=RetryPolicy(max_attempts=1)),
    )
    registry = ToolRegistry()
    registry.register(definition)
    return registry, ToolRuntime(registry), calls, definition


def _python_request(*, max_iterations: int) -> AgentRunRequest:
    return AgentRunRequest(
        messages=(
            ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=USER_MESSAGE),
        ),
        allowed_tools=("knowledge.search",),
        max_iterations=max_iterations,
        max_tool_calls=8,
        timeout_s=5.0,
        max_context_tokens=20_000,
    )


def _pi_request(definition, *, script, max_iterations: int) -> PiSpikeRunRequest:
    return PiSpikeRunRequest(
        run_id="pi_parity_001",
        system_prompt=SYSTEM_PROMPT,
        messages=(PiInputMessage(role="user", content=USER_MESSAGE),),
        allowed_tools=(
            PiAllowedTool(
                name="knowledge.search",
                version="2.0.0",
                description=definition.description,
                input_schema=definition.input_schema,
            ),
        ),
        script=tuple(script),
        policy=PiSpikePolicy(
            max_iterations=max_iterations,
            max_tool_calls=8,
            timeout_s=5.0,
            max_context_chars=20_000,
        ),
    )


def _python_tool_response() -> ChatResponse:
    return ChatResponse(
        content=None,
        model="riftcoach-scripted-model",
        provider="riftcoach-scripted",
        tool_calls=(
            ToolCall(
                id="knowledge_1",
                name="knowledge.search",
                arguments=TOOL_ARGUMENTS,
            ),
        ),
        usage=TokenUsage(input_tokens=6, output_tokens=3),
    )


def _python_final_response() -> ChatResponse:
    return ChatResponse(
        content="evidence received",
        model="riftcoach-scripted-model",
        provider="riftcoach-scripted",
        usage=TokenUsage(input_tokens=7, output_tokens=4),
    )


def _pi_tool_step() -> PiScriptedAssistantStep:
    return PiScriptedAssistantStep(
        tool_calls=(
            PiScriptedToolCall(
                id="knowledge_1",
                name="knowledge.search",
                arguments=TOOL_ARGUMENTS,
            ),
        ),
        usage=PiScriptedUsage(input_tokens=6, output_tokens=3),
    )


def _pi_final_step() -> PiScriptedAssistantStep:
    return PiScriptedAssistantStep(
        content="evidence received",
        usage=PiScriptedUsage(input_tokens=7, output_tokens=4),
    )


def test_pi_and_python_loop_match_successful_tool_order_and_terminal():
    py_registry, py_runtime, py_calls, _ = _knowledge_runtime()
    python_result = AgentLoop(
        provider=ScriptedPythonProvider(
            responses=[_python_tool_response(), _python_final_response()]
        ),
        tool_registry=py_registry,
        tool_runtime=py_runtime,
    ).run(_python_request(max_iterations=4))

    pi_registry, pi_runtime, pi_calls, definition = _knowledge_runtime()
    pi_result = PiSidecarController(
        tool_registry=pi_registry,
        tool_runtime=pi_runtime,
    ).run(
        _pi_request(
            definition,
            script=(_pi_tool_step(), _pi_final_step()),
            max_iterations=4,
        )
    )

    assert python_result.status.value == pi_result.status == "completed"
    assert python_result.stop_reason.value == pi_result.stop_reason == "final_response"
    assert python_result.iterations == pi_result.iterations == 2
    assert python_result.final_response.content == pi_result.final_text
    assert py_calls == pi_calls == [TOOL_ARGUMENTS]
    assert len(python_result.tool_executions) == len(pi_result.tool_executions) == 1
    assert python_result.usage.input_tokens == pi_result.usage.input_tokens == 13
    assert python_result.usage.output_tokens == pi_result.usage.output_tokens == 7


def test_pi_and_python_loop_stop_before_tool_on_final_iteration():
    py_registry, py_runtime, py_calls, _ = _knowledge_runtime()
    python_result = AgentLoop(
        provider=ScriptedPythonProvider(responses=[_python_tool_response()]),
        tool_registry=py_registry,
        tool_runtime=py_runtime,
    ).run(_python_request(max_iterations=1))

    pi_registry, pi_runtime, pi_calls, definition = _knowledge_runtime()
    pi_result = PiSidecarController(
        tool_registry=pi_registry,
        tool_runtime=pi_runtime,
    ).run(
        _pi_request(
            definition,
            script=(_pi_tool_step(),),
            max_iterations=1,
        )
    )

    assert python_result.status.value == pi_result.status == "stopped"
    assert python_result.stop_reason.value == pi_result.stop_reason == "max_iterations"
    assert python_result.iterations == pi_result.iterations == 1
    assert py_calls == pi_calls == []
    assert python_result.tool_executions == ()
    assert pi_result.tool_executions == ()
    assert python_result.usage.input_tokens == pi_result.usage.input_tokens == 6
    assert python_result.usage.output_tokens == pi_result.usage.output_tokens == 3
