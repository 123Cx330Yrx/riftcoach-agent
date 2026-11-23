from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from app.agent.compiler import AgentRunCompiler
from app.agent.context import ContextBuilderV1
from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN,
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
)
from app.evaluation.glm53_low_profile_budget import (
    CandidateEvaluationBudgetError,
    CandidateEvaluationBudgetState,
    CandidateEvaluationBudgetedProvider,
)
from app.model_runtime import (
    CandidateEvaluationRequestPolicy,
    resolve_model_runtime_profile,
    require_candidate_evaluation_request_policy,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
)
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.adapters.llm import build_llm_tools
from app.tools.models import ToolContext, ToolDefinition, ToolPolicy
from app.tools.registry import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RecordingProvider:
    provider_name: str = "zhipu"
    model_name: str = "glm-5.3-flash"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __post_init__(self) -> None:
        self.requests: list[ChatRequest] = []
        self.responses: list[ChatResponse] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        response = (
            self.responses.pop(0)
            if self.responses
            else ChatResponse(
                content="完成",
                model=self.model_name,
                provider=self.provider_name,
                usage=TokenUsage(input_tokens=10, output_tokens=20),
                finish_reason="stop",
            )
        )
        return response


def _knowledge_definition() -> ToolDefinition:
    return ToolDefinition(
        name="knowledge.search",
        version="2.0.0",
        description="Search attributable test knowledge.",
        handler=lambda params, context: {"chunks": []},
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"chunks": {"type": "array"}},
            "required": ["chunks"],
            "additionalProperties": False,
        },
        policy=ToolPolicy(),
    )


def _validated_execution():
    summary = json.loads(
        (ROOT / "examples/fixtures/player_summary_demo.json").read_text(
            encoding="utf-8"
        )
    )
    report = (ROOT / "examples/fixtures/deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )
    utterance = "分析我最近十局的状态"
    catalog = SkillCatalog.from_directory(ROOT / "skills")
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    skill = catalog.get(decision.selected_skill)
    assert skill is not None
    payload = {
        "player_summary": summary,
        "deterministic_report": report,
    }
    typed = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id="candidate_policy_compile",
        player_summary=typed.player_summary,
        deterministic_report=typed.deterministic_report,
    )
    execution = SkillExecutionBoundary(catalog).validate(
        SkillExecutionRequest(
            run_id="candidate_policy_compile",
            user_utterance=utterance,
            router_decision=decision,
            input_payload=payload,
            input_artifacts=binding,
        )
    )
    return execution, ContextBuilderV1().build(execution)


def test_candidate_policy_is_private_exact_and_not_a_product_runtime_profile():
    policy = GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
    assert GLM53_FLASH_LOW_CANDIDATE_PROFILE_PLAN.request_policy is policy
    assert policy.max_output_tokens == 4096
    assert policy.agent_timeout_s == 90.0
    assert policy.llm_tool_timeout_s == 90.0
    assert policy.transport_timeout_s == 120.0
    assert policy.max_retries == 0
    assert policy.max_attempts == 1
    assert policy.deterministic_fallback_allowed is False
    assert resolve_model_runtime_profile(policy.provider_id, policy.model) is not None

    with pytest.raises(ValueError, match="private scope"):
        CandidateEvaluationRequestPolicy(
            policy_id=policy.policy_id,
            version=policy.version,
            provider_id=policy.provider_id,
            model=policy.model,
            agent_timeout_s=90,
            llm_tool_timeout_s=90,
            transport_timeout_s=120,
            max_output_tokens=4096,
            temperature=1,
            top_p=0.95,
        )

    cloned = replace(policy, max_output_tokens=2048)
    with pytest.raises(ValueError, match="issued candidate capability"):
        require_candidate_evaluation_request_policy(cloned)


def test_compiler_applies_candidate_policy_without_runtime_profile_upgrade():
    execution, context = _validated_execution()
    registry = ToolRegistry()
    registry.register(_knowledge_definition())
    request = AgentRunCompiler(
        registry,
        request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    ).compile(execution, context)

    assert request.timeout_s == 90.0
    assert request.max_tokens == 4096
    assert request.temperature == 1.0
    assert request.top_p == 0.95
    assert request.metadata["evaluation_scope"] == "candidate-only"
    assert request.metadata["evaluation_policy_id"] == policy_id()
    with pytest.raises(ValueError, match="mutually exclusive"):
        AgentRunCompiler(
            registry,
            runtime_profile=resolve_model_runtime_profile(
                "zhipu", "glm-5.3-flash"
            ),
            request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
        )


def policy_id() -> str:
    return "glm-5.3-flash-evaluation-low-4096"


def test_llm_tool_candidate_policy_forces_budget_and_one_attempt():
    provider = RecordingProvider()
    definition = build_llm_tools(
        provider,
        request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    )[0]
    assert definition.policy.timeout_s == 90.0
    assert definition.policy.retry.max_attempts == 1
    assert definition.policy.retry.base_delay_s == 0.0
    assert definition.fallback is None
    definition.handler(
        {
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 99999,
            "temperature": 0.0,
            "top_p": 0.1,
        },
        ToolContext(
            call_id="candidate-policy-call",
            attempt=1,
            deadline_monotonic=100.0,
            clock=lambda: 0.0,
        ),
    )
    request = provider.requests[0]
    assert request.max_tokens == 4096
    assert request.temperature == 1.0
    assert request.top_p == 0.95
    assert request.timeout_s == pytest.approx(90.0)
    assert request.metadata["evaluation_policy_id"] == policy_id()
    assert request.metadata["deterministic_fallback_allowed"] is False


def test_candidate_budget_wrapper_reserves_before_io_and_stops_at_case_wall():
    provider = RecordingProvider()
    state = CandidateEvaluationBudgetState()
    state.register_case("case-1")
    controlled = CandidateEvaluationBudgetedProvider(
        provider=provider,
        state=state,
        case_id="case-1",
    )
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "probe"),),
        temperature=0.0,
        max_tokens=9999,
        timeout_s=300.0,
        top_p=0.1,
    )
    for _ in range(4):
        controlled.chat(request)
    assert len(provider.requests) == 4
    assert provider.requests[0].max_tokens == 4096
    assert provider.requests[0].timeout_s == 90.0
    assert provider.requests[0].temperature == 1.0
    assert provider.requests[0].top_p == 0.95
    assert state.snapshot()["calls_used"] == 4
    with pytest.raises(CandidateEvaluationBudgetError, match="external_call_budget"):
        controlled.chat(request)
    assert len(provider.requests) == 4


def test_candidate_budget_wrapper_fail_closes_when_usage_crosses_token_wall():
    provider = RecordingProvider()
    provider.responses.append(
        ChatResponse(
            content="too much",
            model=provider.model_name,
            provider=provider.provider_name,
            usage=TokenUsage(input_tokens=1, output_tokens=24_001),
            finish_reason="stop",
        )
    )
    state = CandidateEvaluationBudgetState()
    state.register_case("case-oversized")
    controlled = CandidateEvaluationBudgetedProvider(
        provider=provider,
        state=state,
        case_id="case-oversized",
    )
    with pytest.raises(CandidateEvaluationBudgetError, match="token_budget"):
        controlled.chat(
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "probe"),),
                max_tokens=4096,
                timeout_s=90,
            )
        )
    assert state.stop_code == "token_budget_exhausted"
    assert state.calls_used == 1
