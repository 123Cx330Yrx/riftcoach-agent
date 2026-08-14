from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, dataclass, field, replace
from pathlib import Path

import pytest

from app.agent.context import ContextBuilderV1
from app.agent.draft import (
    AgentDraftPreparationError,
    AgentDraftPreparationResult,
    AgentFailureObservation,
    SkillAgentDraftPreparer,
)
from app.agent.loop import (
    AgentLoop,
    AgentRunResult,
    AgentRunStatus,
    AgentStopReason,
    ToolExecutionRecord,
)
from app.harness.steps import CoachDraft, KnowledgeEvidence
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.models import (
    ToolDefinition,
    ToolErrorInfo,
    ToolPolicy,
    ToolResult,
)
from app.tools.registry import ToolRegistry
from app.tools.adapters import build_knowledge_tools
from app.tools.runtime import ToolRuntime


FIXTURES = Path("examples/fixtures")


def demo_summary() -> dict:
    return json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )


def demo_report() -> str:
    return (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )


def knowledge_definition() -> ToolDefinition:
    return ToolDefinition(
        name="knowledge.search",
        version="2.0.0",
        description="Search attributable test knowledge.",
        handler=lambda params, context: {
            "provider": "test",
            "abstained": True,
            "diagnostics": {},
            "chunks": [],
            "count": 0,
        },
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "top_k": {"type": "integer", "minimum": 1},
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "abstained": {"type": "boolean"},
                "diagnostics": {"type": "object"},
                "chunks": {"type": "array"},
                "count": {"type": "integer", "minimum": 0},
            },
            "required": [
                "provider",
                "abstained",
                "diagnostics",
                "chunks",
                "count",
            ],
            "additionalProperties": False,
        },
        policy=ToolPolicy(),
    )


def registered_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(knowledge_definition())
    return registry


def validated_execution(*, utterance: str, payload: dict, run_id: str):
    catalog = SkillCatalog.from_directory("skills")
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    skill = catalog.get(decision.selected_skill)
    assert skill is not None
    typed_input = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=typed_input.player_summary,
        deterministic_report=typed_input.deterministic_report,
    )
    return SkillExecutionBoundary(catalog).validate(
        SkillExecutionRequest(
            run_id=run_id,
            user_utterance=utterance,
            router_decision=decision,
            input_payload=payload,
            input_artifacts=binding,
        )
    )


def recent_execution(*, run_id: str = "review_draft_direct"):
    return validated_execution(
        utterance="分析我最近十局的状态",
        payload={
            "player_summary": demo_summary(),
            "deterministic_report": demo_report(),
            "focus": "survival",
        },
        run_id=run_id,
    )


@dataclass
class DirectAnswerProvider:
    provider_name: str = "fake-direct-answer"
    model_name: str = "fake-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content="# Coach draft\n\nOnly deterministic facts were used.",
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )


class StaticResultLoop:
    def __init__(self, result: AgentRunResult, registry: ToolRegistry) -> None:
        self.result = result
        self.tool_registry = registry
        self.requests = []

    def run(self, request):
        self.requests.append(request)
        return self.result


@dataclass
class KnowledgeSeekingProvider:
    provider_name: str = "fake-knowledge-agent"
    model_name: str = "fake-knowledge-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
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
        if not observation["success"]:
            return ChatResponse(
                content="# Draft after a failed tool observation",
                model=self.model_name,
                provider=self.provider_name,
            )
        actual_sources = [
            row["source_id"] for row in observation["data"]["chunks"]
        ]
        return ChatResponse(
            content=(
                "# Coach draft\n\n"
                f"Actual tool sources: {', '.join(actual_sources)}.\n\n"
                "The model also claims ghost-only.md, which was never retrieved."
            ),
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=20, output_tokens=10),
        )


def completed_result(
    *,
    final_response: ChatResponse | None = None,
    tool_executions: tuple[ToolExecutionRecord, ...] = (),
) -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.COMPLETED,
        stop_reason=AgentStopReason.FINAL_RESPONSE,
        messages=(),
        provider_responses=(),
        tool_executions=tool_executions,
        usage=TokenUsage(),
        iterations=1,
        final_response=final_response,
    )


def final_response(content: str = "# Draft") -> ChatResponse:
    return ChatResponse(
        content=content,
        model="fake-model",
        provider="fake-provider",
    )


def test_direct_final_response_returns_immutable_unpublished_draft():
    execution = recent_execution()
    context = ContextBuilderV1().build(execution)
    registry = registered_tools()
    provider = DirectAnswerProvider()
    loop = AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(registry),
    )

    result = SkillAgentDraftPreparer(loop).prepare(execution, context)

    assert isinstance(result, AgentDraftPreparationResult)
    assert result.draft == CoachDraft(
        report="# Coach draft\n\nOnly deterministic facts were used."
    )
    assert result.knowledge == KnowledgeEvidence.empty()
    assert result.agent_run.status is AgentRunStatus.COMPLETED
    assert result.agent_run.tool_executions == ()
    assert provider.requests[0].metadata["run_id"] == execution.run_id
    with pytest.raises(FrozenInstanceError):
        result.draft = CoachDraft(report="changed")


@pytest.mark.parametrize(
    ("status", "stop_reason"),
    (
        (AgentRunStatus.STOPPED, AgentStopReason.MAX_ITERATIONS),
        (AgentRunStatus.STOPPED, AgentStopReason.MAX_TOOL_CALLS),
        (AgentRunStatus.STOPPED, AgentStopReason.DUPLICATE_TOOL_CALL),
        (AgentRunStatus.STOPPED, AgentStopReason.TIMEOUT),
        (AgentRunStatus.FAILED, AgentStopReason.PROVIDER_ERROR),
    ),
)
def test_non_completed_agent_runs_fail_with_safe_state(
    status: AgentRunStatus,
    stop_reason: AgentStopReason,
):
    execution = recent_execution(run_id=f"review_{status.value}")
    context = ContextBuilderV1().build(execution)
    loop = StaticResultLoop(
        AgentRunResult(
            status=status,
            stop_reason=stop_reason,
            messages=(),
            provider_responses=(),
            tool_executions=(),
            usage=TokenUsage(),
            iterations=1,
            error_code="safe_provider_code",
        ),
        registered_tools(),
    )

    with pytest.raises(
        AgentDraftPreparationError,
        match=f"{status.value}.*{stop_reason.value}",
    ) as captured:
        SkillAgentDraftPreparer(loop).prepare(execution, context)

    assert captured.value.failure == AgentFailureObservation(
        status=status,
        stop_reason=stop_reason,
        error_code="safe_provider_code",
    )


def test_completed_run_without_final_text_fails_closed():
    execution = recent_execution(run_id="review_missing_final")
    context = ContextBuilderV1().build(execution)
    loop = StaticResultLoop(completed_result(), registered_tools())

    with pytest.raises(AgentDraftPreparationError, match="final text"):
        SkillAgentDraftPreparer(loop).prepare(execution, context)


def test_failed_knowledge_execution_surfaces_only_safe_error_code():
    execution = recent_execution(run_id="review_failed_knowledge")
    context = ContextBuilderV1().build(execution)
    failed = ToolResult.fail(
        error=ToolErrorInfo(
            code="invalid_knowledge_output",
            message="secret raw upstream payload",
        ),
        tool_name="knowledge.search",
        tool_version="2.0.0",
        call_id="runtime-call",
        attempts=1,
        latency_ms=1.0,
    )
    run = completed_result(
        final_response=final_response(),
        tool_executions=(
            ToolExecutionRecord(
                tool_call_id="knowledge-call",
                tool_name="knowledge.search",
                arguments={"query": "test", "top_k": 1},
                result=failed,
            ),
        ),
    )
    loop = StaticResultLoop(run, registered_tools())

    with pytest.raises(AgentDraftPreparationError) as captured:
        SkillAgentDraftPreparer(loop).prepare(execution, context)

    assert "invalid_knowledge_output" in str(captured.value)
    assert "secret raw upstream payload" not in str(captured.value)


def test_unsupported_non_knowledge_execution_fails_closed():
    execution = recent_execution(run_id="review_unsupported_tool")
    context = ContextBuilderV1().build(execution)
    unsupported = ToolResult.ok(
        data={"matches": []},
        tool_name="riot.recent_matches",
        tool_version="1.0.0",
        call_id="runtime-call",
        attempts=1,
        latency_ms=1.0,
    )
    run = completed_result(
        final_response=final_response(),
        tool_executions=(
            ToolExecutionRecord(
                tool_call_id="other-call",
                tool_name="riot.recent_matches",
                arguments={},
                result=unsupported,
            ),
        ),
    )
    loop = StaticResultLoop(run, registered_tools())

    with pytest.raises(AgentDraftPreparationError, match="unsupported tool"):
        SkillAgentDraftPreparer(loop).prepare(execution, context)


@pytest.mark.parametrize(
    ("utterance", "payload", "run_id", "expected_skill"),
    (
        (
            "分析我最近十局的状态",
            {
                "player_summary": demo_summary(),
                "deterministic_report": demo_report(),
                "focus": "survival",
            },
            "review_agent_recent_real_rag",
            "recent-form-review",
        ),
        (
            "深入复盘这一场的表现",
            {
                "player_summary": demo_summary(),
                "deterministic_report": demo_report(),
                "target_match_id": "SYNTHETIC_WIN_001",
                "focus": "laning",
            },
            "review_agent_single_real_rag",
            "single-match-review",
        ),
    ),
)
def test_both_real_skills_prepare_draft_from_real_knowledge_execution(
    utterance: str,
    payload: dict,
    run_id: str,
    expected_skill: str,
):
    execution = validated_execution(
        utterance=utterance,
        payload=payload,
        run_id=run_id,
    )
    context = ContextBuilderV1().build(execution)
    registry = ToolRegistry()
    for definition in build_knowledge_tools(
        LocalHybridKnowledgeProvider.from_directory(Path("data/rag_docs"))
    ):
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

    result = SkillAgentDraftPreparer(loop).prepare(execution, context)

    assert execution.skill.manifest.name == expected_skill
    assert result.agent_run.status is AgentRunStatus.COMPLETED
    assert len(result.agent_run.tool_executions) == 1
    tool_execution = result.agent_run.tool_executions[0]
    assert tool_execution.tool_name == "knowledge.search"
    assert tool_execution.result.success is True
    assert result.knowledge.abstained is False
    assert result.knowledge.citations
    assert [item.citation_id for item in result.knowledge.citations] == [
        f"K{index}"
        for index in range(1, len(result.knowledge.citations) + 1)
    ]
    assert result.knowledge.source_ids == tuple(
        dict.fromkeys(
            item.source_id for item in result.knowledge.citations
        )
    )
    assert "ghost-only.md" in result.draft.report
    assert "ghost-only.md" not in result.knowledge.source_ids
    assert "ghost-only.md" not in result.knowledge.context
    assert provider.requests[0].metadata["run_id"] == run_id
    assert provider.requests[0].metadata["skill_name"] == expected_skill
    assert provider.requests[0].metadata["skill_version"] == (
        execution.skill.manifest.version
    )


def test_real_tool_runtime_output_schema_failure_returns_no_preparation_result():
    execution = recent_execution(run_id="review_bad_tool_output")
    context = ContextBuilderV1().build(execution)
    registry = ToolRegistry()
    registry.register(
        replace(
            knowledge_definition(),
            handler=lambda params, tool_context: {
                "provider": "malformed-only"
            },
        )
    )
    provider = KnowledgeSeekingProvider()
    loop = AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(registry),
    )

    with pytest.raises(AgentDraftPreparationError) as captured:
        SkillAgentDraftPreparer(loop).prepare(execution, context)

    assert "invalid_tool_output" in str(captured.value)
    assert "malformed-only" not in str(captured.value)
    assert len(provider.requests) == 2
