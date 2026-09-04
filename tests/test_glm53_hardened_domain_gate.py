from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.evaluation.glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
)
from app.evaluation.glm53_hardened_domain_assets import CASE_IDS, PROTOCOL_ID
from app.evaluation.glm53_hardened_domain_gate import (
    HardenedDomainGateOptions,
    HardenedDomainGateResult,
    build_hardened_domain_preflight,
    canonical_hardened_result_bytes,
    run_cli,
    run_hardened_domain_gate,
)
from app.evaluation.provider_domain_experiment import DomainCaseSemanticObservation
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage


ROOT = Path(__file__).resolve().parents[1]


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


class PassingHardenedExecutor:
    def __init__(self, execution_plan, *, quality_hardening: bool = True) -> None:
        self.execution_plan = execution_plan
        self.runtime_profile = None
        self.request_policy = GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        self.quality_hardening = quality_hardening

    def execute(self, *, case_id: str, provider) -> DomainCaseSemanticObservation:
        for _ in range(3):
            provider.chat(
                ChatRequest(
                    messages=(ChatMessage(role=MessageRole.USER, content="probe"),),
                    max_tokens=4096,
                    timeout_s=90.0,
                )
            )
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


def _head_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _prepared():
    sha = _head_sha()
    return build_hardened_domain_preflight(
        project_root=ROOT,
        implementation_sha=sha,
        public_ci_sha=sha,
        confirm_public_ci_success=True,
    )


def test_hardened_preflight_binds_v2_assets_without_provider_io() -> None:
    prepared = _prepared()

    assert prepared.admission.protocol_id == PROTOCOL_ID
    assert prepared.admission.asset_admission.case_ids == CASE_IDS
    assert prepared.admission.quality_hardening_version == (
        "glm53-flash-domain-quality-v1"
    )
    assert prepared.admission.minimum_evidence_sources == 1
    assert prepared.admission.external_provider_calls == 0
    assert prepared.admission.held_out_executed is False


def test_hardened_gate_uses_quality_boundary_and_v2_identity() -> None:
    prepared = _prepared()
    provider = ScriptedProvider()
    result = run_hardened_domain_gate(
        admission=prepared.admission,
        dataset=prepared.dataset,
        provider=provider,
        case_executor=PassingHardenedExecutor(prepared.input_plan.execution_plan),
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
        clock=lambda: 100.0,
    )

    assert isinstance(result, HardenedDomainGateResult)
    assert result.protocol_id == PROTOCOL_ID
    assert result.admitted is True
    assert result.domain_calls_used == 9
    assert result.network_used is True
    assert result.quality_hardening_version == "glm53-flash-domain-quality-v1"
    assert result.minimum_evidence_sources == 1
    assert result.candidate_registered is False
    assert result.production_admitted is False
    assert all(request.max_tokens == 4096 for request in provider.requests)
    assert all(request.temperature == 1.0 for request in provider.requests)
    assert all(request.top_p == 0.95 for request in provider.requests)
    assert all(request.timeout_s == 90.0 for request in provider.requests)


def test_hardened_gate_rejects_executor_without_quality_hardening() -> None:
    prepared = _prepared()
    executor = PassingHardenedExecutor(
        prepared.input_plan.execution_plan,
        quality_hardening=False,
    )

    with pytest.raises(ValueError, match="quality hardening"):
        run_hardened_domain_gate(
            admission=prepared.admission,
            dataset=prepared.dataset,
            provider=ScriptedProvider(),
            case_executor=executor,
        )


def test_hardened_gate_requires_explicit_real_call_confirmation() -> None:
    prepared = _prepared()

    with pytest.raises(RuntimeError, match="explicit confirmation"):
        run_hardened_domain_gate(
            admission=prepared.admission,
            dataset=prepared.dataset,
            provider=ScriptedProvider(),
            case_executor=PassingHardenedExecutor(
                prepared.input_plan.execution_plan
            ),
            confirm_real_call=False,
        )


def test_hardened_cli_preflight_never_loads_environment_or_provider() -> None:
    sha = _head_sha()

    result = run_cli(
        HardenedDomainGateOptions(
            confirm_real_call=False,
            preflight_only=True,
            implementation_sha=sha,
            public_ci_sha=sha,
        ),
        repository_root=ROOT,
        environment_loader=lambda _root: (_ for _ in ()).throw(
            AssertionError("environment must not be loaded")
        ),
        provider_factory=lambda _settings: (_ for _ in ()).throw(
            AssertionError("provider must not be constructed")
        ),
    )

    assert result.external_provider_calls == 0
    assert result.held_out_executed is False


def test_hardened_result_serialization_is_body_free() -> None:
    prepared = _prepared()
    result = run_hardened_domain_gate(
        admission=prepared.admission,
        dataset=prepared.dataset,
        provider=ScriptedProvider(),
        case_executor=PassingHardenedExecutor(prepared.input_plan.execution_plan),
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
        clock=lambda: 100.0,
    )

    serialized = canonical_hardened_result_bytes(result).decode("utf-8")
    for forbidden in (
        "HARBOR_USER_DATA_592",
        "HARBOR_KNOWLEDGE_DATA_841",
        '"content"',
        '"reasoning"',
        '"messages"',
        '"api_key"',
    ):
        assert forbidden not in serialized
