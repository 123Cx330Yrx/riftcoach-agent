from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
)
from app.evaluation.glm53_low_profile_domain_gate import (
    LowProfileDomainGateResult,
    build_low_profile_preflight,
    run_low_profile_domain_gate,
)
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/glm53_flash_low_profile_domain_heldout_v1.json"
PLAN = ROOT / "data/evaluation/glm53_flash_low_profile_domain_v1_1_input_plan.json"


@dataclass
class ScriptedProvider:
    provider_name: str = "zhipu"
    model_name: str = "glm-5.3-flash"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __post_init__(self) -> None:
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content="ok",
            model=self.model_name,
            provider=self.provider_name,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
            request_id=None,
        )


class PassingExecutor:
    def __init__(self, execution_plan) -> None:
        self.execution_plan = execution_plan
        self.runtime_profile = None
        self.request_policy = GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY

    def execute(self, *, case_id: str, provider) -> object:
        for _ in range(3):
            provider.chat(
                ChatRequest(
                    messages=(
                        ChatMessage(role=MessageRole.USER, content="probe"),
                    ),
                    max_tokens=4096,
                    timeout_s=90.0,
                )
            )
        from app.evaluation.provider_domain_experiment import DomainCaseSemanticObservation

        return DomainCaseSemanticObservation(
            case_id=case_id,
            normalized_response_count=3,
            safe_provider_error_code=None,
            agent_status="completed",
            agent_stop_reason="final_response",
            proposed_tool_names=("knowledge.search",),
            successful_tool_names=("knowledge.search",),
            evidence_source_ids=("K1",),
            fact_check_passed=True,
            citation_check_passed=True,
            injection_check_passed=True,
            evaluation_validated=True,
            evaluation_score=95,
            terminal_status="published",
            terminal_reason="published",
            provenance_sha256="a" * 64,
        )


def _admission():
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    prepared = build_low_profile_preflight(
        project_root=ROOT,
        implementation_sha=sha,
        public_ci_sha=sha,
        confirm_public_ci_success=True,
    )
    return prepared


def test_preflight_rebuilds_fresh_assets_without_provider_io() -> None:
    prepared = _admission()
    assert prepared.admission.external_provider_calls == 0
    assert prepared.admission.candidate_registered is False
    assert prepared.admission.execution_plan.case_ids == (
        "low_gate_baseline_17",
        "low_gate_user_boundary_23",
        "low_gate_knowledge_boundary_31",
    )


def test_domain_gate_uses_low_policy_and_admits_passing_cases() -> None:
    prepared = _admission()
    provider = ScriptedProvider()
    result = run_low_profile_domain_gate(
        admission=prepared.admission,
        dataset=prepared.dataset,
        provider=provider,
        case_executor=PassingExecutor(prepared.input_plan.execution_plan),
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
        clock=lambda: 100.0,
    )

    assert isinstance(result, LowProfileDomainGateResult)
    assert result.admitted is True
    assert result.domain_calls_used == 9
    assert result.domain_total_tokens == 135
    assert result.network_used is True
    assert result.candidate_registered is False
    assert result.production_admitted is False
    assert all(request.max_tokens == 4096 for request in provider.requests)
    assert all(request.temperature == 1.0 for request in provider.requests)
    assert all(request.top_p == 0.95 for request in provider.requests)
    assert all(request.timeout_s == 90.0 for request in provider.requests)


def test_domain_gate_rejects_product_runtime_executor() -> None:
    prepared = _admission()
    executor = PassingExecutor(prepared.input_plan.execution_plan)
    executor.runtime_profile = object()
    with pytest.raises(ValueError, match="product runtime profile"):
        run_low_profile_domain_gate(
            admission=prepared.admission,
            dataset=prepared.dataset,
            provider=ScriptedProvider(),
            case_executor=executor,
        )
