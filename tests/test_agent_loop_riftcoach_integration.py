from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.agent.loop import AgentLoop, AgentRunRequest, AgentRunStatus
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.tools.adapters import build_knowledge_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


@dataclass
class KnowledgeSeekingProvider:
    """Deterministic model double; the RAG tool below is the real implementation."""

    provider_name: str = "fake-knowledge-agent"
    model_name: str = "fake-knowledge-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if request.messages[-1].role is not MessageRole.TOOL:
            return ChatResponse(
                content=None,
                model=self.model_name,
                provider=self.provider_name,
                tool_calls=(
                    ToolCall(
                        id="knowledge-call-1",
                        name="knowledge.search",
                        arguments={
                            "query": "Data Dragon 能提供英雄胜率吗",
                            "top_k": 2,
                        },
                    ),
                ),
                usage=TokenUsage(input_tokens=10, output_tokens=6),
            )

        observation = json.loads(request.messages[-1].content)
        source_ids = [
            chunk["source_id"]
            for chunk in observation["data"]["chunks"]
        ]
        return ChatResponse(
            content=f"已根据 {', '.join(source_ids)} 回答。",
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=20, output_tokens=8),
        )


def test_agent_loop_calls_real_riftcoach_knowledge_tool():
    knowledge_provider = LocalHybridKnowledgeProvider.from_directory(
        Path("data/rag_docs")
    )
    registry = ToolRegistry()
    for definition in build_knowledge_tools(knowledge_provider):
        registry.register(definition)

    provider = KnowledgeSeekingProvider()
    loop = AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(
            registry,
            call_id_factory=lambda: "knowledge-runtime-call",
        ),
    )

    result = loop.run(
        AgentRunRequest(
            messages=(
                ChatMessage(
                    role=MessageRole.USER,
                    content="Data Dragon 能提供英雄胜率吗？",
                ),
            ),
            allowed_tools=("knowledge.search",),
        )
    )

    assert result.status is AgentRunStatus.COMPLETED
    assert result.final_response is not None
    assert "04_data_boundaries.md" in result.final_response.content
    assert len(result.tool_executions) == 1

    execution = result.tool_executions[0]
    assert execution.tool_name == "knowledge.search"
    assert execution.result.success is True
    assert execution.result.data["abstained"] is False
    assert any(
        chunk["source_id"] == "04_data_boundaries.md"
        for chunk in execution.result.data["chunks"]
    )

    assert len(provider.requests) == 2
    assert [tool.name for tool in provider.requests[0].tools] == [
        "knowledge.search"
    ]
    assert provider.requests[1].messages[-1].role is MessageRole.TOOL
    assert provider.requests[1].messages[-1].tool_call_id == "knowledge-call-1"
