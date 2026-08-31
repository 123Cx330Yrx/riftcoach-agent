from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.evaluation.domain_e2e import DomainCaseResult
from app.evaluation.glm53_domain_gate import (
    CASE_MAX_CALLS,
    DOMAIN_MAX_CALLS,
    GLM53BudgetState,
    GLM53BudgetedProvider,
    GLM53FreshDomainAdmission,
    GLM53FreshDomainResult,
    PUBLIC_CI_SHA,
    build_glm53_preflight,
    run_glm53_domain_gate,
)
from app.evaluation.provider_domain_experiment import (
    ImmutableDomainExperimentOutput,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.model_runtime import GLM53_FLASH_RUNTIME_PROFILE
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderAuthenticationError, ProviderResponseError
from app.providers.models import ChatResponse, TokenUsage, ToolCall


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_cases.json"
PLAN = ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json"
SNAPSHOT = ROOT / "data/evaluation/contracts/glm53_flash_recent_form_prompt_context_v1.json"
PROTOCOL = ROOT / (
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_adapter_protocol_retry2.json"
)


def _preflight():
    return build_glm53_preflight(
        project_root=ROOT,
        dataset_path=DATASET,
        input_plan_path=PLAN,
        snapshot_path=SNAPSHOT,
        protocol_result_path=PROTOCOL,
        code_sha=PUBLIC_CI_SHA,
        public_ci_sha=PUBLIC_CI_SHA,
        confirm_public_ci_success=True,
    )


class _CompleteProvider:
    provider_name = "zhipu"
    model_name = "glm-5.3-flash"
    capabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __init__(self) -> None:
        self.calls = 0
        self.requests = []

    def chat(self, request):
        self.calls += 1
        self.requests.append(request)
        if request.response_contract is not None:
            content = json.dumps(
                {
                    "score": 95,
                    "verdict": "pass",
                    "issues": [],
                    "passed_checks": ["facts", "citations", "security"],
                    "summary": "safe evaluation",
                },
                ensure_ascii=False,
            )
            return ChatResponse(
                content=content,
                model=self.model_name,
                provider=self.provider_name,
                usage=TokenUsage(input_tokens=10, output_tokens=10),
                finish_reason="stop",
            )
        if any(message.role.value == "tool" for message in request.messages):
            return ChatResponse(
                content="# 近期复盘\n\n建议关注前期死亡 [K1]。",
                model=self.model_name,
                provider=self.provider_name,
                usage=TokenUsage(input_tokens=10, output_tokens=10),
                finish_reason="stop",
            )
        return ChatResponse(
            content=None,
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=10, output_tokens=10),
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id=f"call-{self.calls}",
                    name="knowledge.search",
                    arguments={"query": "前期死亡", "top_k": 2},
                ),
            ),
        )


class _AuthenticationProvider(_CompleteProvider):
    def chat(self, request):
        self.calls += 1
        raise ProviderAuthenticationError(
            provider=self.provider_name,
            code="authentication_failed",
        )


def test_preflight_is_no_io_and_binds_frozen_identities():
    prepared = _preflight()
    assert isinstance(prepared.admission, GLM53FreshDomainAdmission)
    assert prepared.admission.external_provider_calls == 0
    assert prepared.admission.held_out_executed is False
    assert prepared.admission.runtime_profile_id == GLM53_FLASH_RUNTIME_PROFILE.profile_id
    assert prepared.admission.runtime_profile_version == GLM53_FLASH_RUNTIME_PROFILE.version
    assert prepared.admission.max_output_tokens_per_request == 2048
    assert prepared.admission.protocol_calls == 3
    assert prepared.admission.execution_plan.case_ids == (
        "flash_gate_baseline_01",
        "flash_gate_user_guard_02",
        "flash_gate_knowledge_guard_03",
    )
    payload = json.loads(prepared.admission.model_dump_json())
    forbidden_keys = {"api_key", "request_id", "raw_prompt", "raw_response"}

    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert forbidden_keys.isdisjoint(keys(payload))
    serialized = prepared.admission.model_dump_json()
    assert "AURORA_CIPHER_418" not in serialized
    assert "NEBULA_TRACE_629" not in serialized


def test_preflight_rejects_historical_protocol_for_a_new_code_sha():
    with pytest.raises(ValueError, match="protocol code SHA"):
        build_glm53_preflight(
            project_root=ROOT,
            dataset_path=DATASET,
            input_plan_path=PLAN,
            snapshot_path=SNAPSHOT,
            protocol_result_path=PROTOCOL,
            code_sha="a" * 40,
            public_ci_sha="a" * 40,
            confirm_public_ci_success=True,
        )


def test_fake_provider_completes_all_three_cases_within_glm_budget():
    prepared = _preflight()
    provider = _CompleteProvider()
    with tempfile.TemporaryDirectory(prefix="glm53-gate-test-") as directory:
        executor = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=prepared.input_plan,
            runs_root=Path(directory),
            runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
        )
        result = run_glm53_domain_gate(
            admission=prepared.admission,
            dataset=prepared.dataset,
            provider=provider,
            case_executor=executor,
            clock=lambda: 0.0,
        )
    assert isinstance(result, GLM53FreshDomainResult)
    assert result.admitted is True
    assert result.domain_calls_used == 9
    assert result.cumulative_calls_used == 12
    assert provider.calls == 9
    assert all(request.max_tokens == 2048 for request in provider.requests)
    assert all(request.temperature == 1.0 for request in provider.requests)
    assert all(request.top_p == 0.95 for request in provider.requests)
    assert all(request.timeout_s <= 90.0 for request in provider.requests)
    assert result.evaluation is not None
    assert result.evaluation.task_outcome_accuracy == 1.0
    assert result.evaluation.failure_classification_accuracy == 1.0
    assert result.monetary_cost_status == "unknown"


def test_first_provider_error_stops_and_skips_remaining_cases():
    prepared = _preflight()
    provider = _AuthenticationProvider()
    with tempfile.TemporaryDirectory(prefix="glm53-gate-auth-") as directory:
        executor = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=prepared.input_plan,
            runs_root=Path(directory),
            runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
        )
        result = run_glm53_domain_gate(
            admission=prepared.admission,
            dataset=prepared.dataset,
            provider=provider,
            case_executor=executor,
            clock=lambda: 0.0,
        )
    assert provider.calls == 1
    assert result.admitted is False
    assert [row.status for row in result.cases] == [
        "executed",
        "skipped",
        "skipped",
    ]
    assert result.cases[0].failure_code is not None
    assert result.resources.stop_code is not None
    assert result.control.provider_stops[0].provider_error_code == (
        "authentication_failed"
    )


def test_budget_wrapper_blocks_fifth_case_call_before_delegate():
    prepared = _preflight()
    state = GLM53BudgetState()
    state.register_case(prepared.admission.execution_plan.case_ids[0])
    provider = _CompleteProvider()
    controlled = GLM53BudgetedProvider(
        provider=provider,
        state=state,
        case_id=prepared.admission.execution_plan.case_ids[0],
    )
    from app.providers.models import ChatMessage, ChatRequest, MessageRole

    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, "probe"),),
        max_tokens=1,
        top_p=0.95,
    )
    for _ in range(CASE_MAX_CALLS):
        controlled.chat(request)
    with pytest.raises(ProviderResponseError, match="external_call_budget_exhausted"):
        controlled.chat(request)
    assert provider.calls == CASE_MAX_CALLS
    assert state.calls_used == CASE_MAX_CALLS
    assert [item.top_p for item in provider.requests] == [0.95] * CASE_MAX_CALLS


def test_budget_wrapper_uses_full_flash_default_output_cap():
    prepared = _preflight()
    state = GLM53BudgetState()
    case_id = prepared.admission.execution_plan.case_ids[0]
    state.register_case(case_id)
    provider = _CompleteProvider()
    controlled = GLM53BudgetedProvider(
        provider=provider,
        state=state,
        case_id=case_id,
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    from app.providers.models import ChatMessage, ChatRequest, MessageRole

    controlled.chat(
        ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "probe"),),
            top_p=0.95,
        )
    )

    assert provider.requests[0].max_tokens == 2048
    assert provider.requests[0].top_p == 0.95


def test_immutable_output_reservation_rejects_duplicate_and_keeps_safe_result(tmp_path):
    prepared = _preflight()
    output = tmp_path / "result.json"
    reservation = ImmutableDomainExperimentOutput.reserve(
        output,
        experiment_id=prepared.admission.experiment_id,
    )
    with pytest.raises(FileExistsError):
        ImmutableDomainExperimentOutput.reserve(
            output,
            experiment_id=prepared.admission.experiment_id,
        )
    reservation.abandon()
    assert output.read_bytes() == b""
