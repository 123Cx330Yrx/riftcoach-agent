from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.provider_domain_production import (
    ProductionDomainCaseExecutor,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderAuthenticationError
from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
PLAN = ROOT / "data/evaluation/deepseek_v4_pro_domain_heldout_input_plan.json"


@dataclass
class SafeProvider:
    provider_name: str = "offline-production-provider"
    model_name: str = "offline-production-model"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if request.response_contract is not None:
            content = json.dumps(
                {
                    "score": 95,
                    "verdict": "pass",
                    "issues": [],
                    "passed_checks": ["facts", "citations", "security"],
                    "summary": "controlled pass",
                },
                ensure_ascii=False,
            )
            return self._text(content)
        if any(message.role.value == "tool" for message in request.messages):
            return self._text(
                "# RiftCoach 复盘\n\n建议优先练习前期生存，并以 [K1] 作为知识依据。"
            )
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id="production-knowledge-1",
                    name="knowledge.search",
                    arguments={"query": "早期死亡", "top_k": 2},
                ),
            ),
            usage=TokenUsage(input_tokens=20, output_tokens=5),
        )

    def _text(self, content: str) -> ChatResponse:
        return ChatResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=20, output_tokens=10),
        )


@dataclass
class InjectionAwareProvider(SafeProvider):
    marker: str = ""

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        combined = "\n".join(message.content or "" for message in request.messages)
        if request.response_contract is not None:
            if self.marker in combined:
                return self._text(
                    json.dumps(
                        {
                            "score": 20,
                            "verdict": "fail",
                            "issues": [
                                {
                                    "severity": "high",
                                    "category": "prompt_injection",
                                    "quote": "controlled marker",
                                    "evidence": "draft followed untrusted data",
                                    "explanation": "security policy blocked",
                                    "suggested_correction": "fallback",
                                }
                            ],
                            "passed_checks": ["schema"],
                            "summary": "blocked",
                        },
                        ensure_ascii=False,
                    )
                )
        if any(message.role.value == "tool" for message in request.messages):
            return self._text(f"# 复盘\n\n[K1] {self.marker}")
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id="injection-knowledge-1",
                    name="knowledge.search",
                    arguments={"query": "早期死亡", "top_k": 2},
                ),
            ),
            usage=TokenUsage(input_tokens=20, output_tokens=5),
        )


@dataclass
class NeedsRevisionProvider(SafeProvider):
    def chat(self, request: ChatRequest) -> ChatResponse:
        if request.response_contract is None:
            return super().chat(request)
        self.requests.append(request)
        return self._text(
            json.dumps(
                {
                    "score": 70,
                    "verdict": "needs_revision",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "fact_error",
                            "quote": "controlled",
                            "evidence": "controlled",
                            "explanation": "controlled",
                            "suggested_correction": "controlled",
                        }
                    ],
                    "passed_checks": ["schema"],
                    "summary": "revision requested",
                },
                ensure_ascii=False,
            )
        )


@dataclass
class AuthenticationFailingProvider(SafeProvider):
    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        raise ProviderAuthenticationError(
            provider="deepseek",
            code="authentication_failed",
        )


def test_production_executor_runs_real_local_skill_rag_and_harness():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = SafeProvider()
    with tempfile.TemporaryDirectory() as directory:
        executor = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        )
        observation = executor.execute(
            case_id="heldout_recent_form_normal",
            provider=provider,
        )

    assert observation.case_id == "heldout_recent_form_normal"
    assert observation.agent_status == "completed"
    assert observation.agent_stop_reason == "final_response"
    assert observation.proposed_tool_names == ("knowledge.search",)
    assert observation.successful_tool_names == ("knowledge.search",)
    assert observation.evidence_source_ids
    assert observation.fact_check_passed is True
    assert observation.citation_check_passed is True
    assert observation.injection_check_passed is True
    assert observation.evaluation_validated is True
    assert observation.evaluation_score == 95
    assert observation.terminal_status == "published"
    assert observation.normalized_response_count == 3
    assert len(provider.requests) == 3


def test_production_executor_keeps_case_input_private_from_executor_method():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    executor = ProductionDomainCaseExecutor(
        project_root=ROOT,
        input_plan=plan,
        runs_root=ROOT / "tmp" / "production-test-runs",
    )

    assert executor.execution_plan.case_ids == tuple(
        row.case_id for row in dataset.cases
    )
    assert not hasattr(executor, "dataset")


def test_production_executor_observes_user_and_knowledge_injection_markers():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    for case_id, marker in (
        ("heldout_user_request_instruction", "USER_INJECTION_ACCEPTED"),
        ("heldout_retrieved_evidence_instruction", "KNOWLEDGE_INJECTION_ACCEPTED"),
    ):
        provider = InjectionAwareProvider(marker=marker)
        with tempfile.TemporaryDirectory() as directory:
            observation = ProductionDomainCaseExecutor(
                project_root=ROOT,
                input_plan=plan,
                runs_root=directory,
            ).execute(case_id=case_id, provider=provider)
        assert observation.injection_check_passed is False
        assert observation.terminal_status == "degraded"
        assert observation.terminal_reason == "security_policy_blocked"
        assert observation.evaluation_validated is True
        assert observation.evaluation_score == 20


def test_production_executor_preserves_safe_agent_failure_provenance():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = AuthenticationFailingProvider()
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        ).execute(
            case_id="heldout_recent_form_normal",
            provider=provider,
        )

    assert observation.agent_status == "failed"
    assert observation.agent_stop_reason == "provider_error"
    assert observation.safe_provider_error_code == "authentication_failed"
    assert observation.normalized_response_count == 0
    assert observation.terminal_status == "degraded"
    assert observation.terminal_reason == "draft_preparation_failed"


def test_production_executor_disables_revision_calls_for_heldout():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = NeedsRevisionProvider()
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        ).execute(
            case_id="heldout_recent_form_normal",
            provider=provider,
        )

    assert observation.normalized_response_count == 3
    assert len(provider.requests) == 3
    assert observation.terminal_status == "degraded"
    assert observation.terminal_reason == "revision_budget_exhausted"
