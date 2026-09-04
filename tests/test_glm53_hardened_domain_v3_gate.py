from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.glm53_bounded_revision_budget_reachability import load_v3_budget_reachability_report
from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
from app.evaluation.glm53_hardened_domain_v3_assets import (
    CASE_IDS,
    DATASET_PATH,
    INPUT_PLAN_PATH,
    PROTOCOL_ID,
    PROTOCOL_PATH,
    SNAPSHOT_PATH,
    admit_hardened_domain_v3_assets,
)
from app.evaluation.glm53_hardened_domain_v3_gate import (
    DEFAULT_PROTOCOL_RESULT,
    V3DomainAdmission,
    V3DomainGateOptions,
    V3DomainGateResult,
    V3PreflightStatus,
    _admission_identity,
    canonical_v3_result_bytes,
    run_cli,
    run_v3_domain_gate,
)
from app.evaluation.glm53_bounded_revision_budget_reachability import _digest_json
from app.evaluation.provider_domain_experiment import DomainCaseSemanticObservation
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage


ROOT = Path(__file__).resolve().parents[1]


def head_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


@dataclass
class ScriptedProvider:
    provider_name: str = "zhipu"
    model_name: str = "glm-5.3-flash"
    capabilities: ProviderCapabilities = ProviderCapabilities(text_chat=True, tool_calling=True, structured_output=True)

    def __post_init__(self):
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(content="ok", provider=self.provider_name, model=self.model_name, finish_reason="stop", usage=TokenUsage(input_tokens=10, output_tokens=5))


class PassingExecutor:
    def __init__(self, execution_plan):
        self.execution_plan = execution_plan
        self.runtime_profile = None
        self.request_policy = GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        self.quality_hardening = True
        self.max_revisions = 1

    def execute(self, *, case_id: str, provider) -> DomainCaseSemanticObservation:
        for _ in range(3):
            provider.chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, "probe"),), max_tokens=4096))
        return DomainCaseSemanticObservation(
            case_id=case_id,
            normalized_response_count=3,
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


def admission():
    assets = admit_hardened_domain_v3_assets(project_root=ROOT, confirm_rules_frozen=True)
    dataset = load_domain_dataset(ROOT / DATASET_PATH)
    plan = load_domain_case_input_plan(
        ROOT / INPUT_PLAN_PATH,
        project_root=ROOT,
        dataset=dataset,
        expected_max_revisions=1,
    )
    budget = load_v3_budget_reachability_report(ROOT / "data/evaluation/contracts/glm53_flash_hardened_v3_budget_reachability.json")
    sha = head_sha()
    values = {
        "experiment_id": "0" * 64,
        "implementation_sha": sha,
        "public_ci_sha": sha,
        "public_ci_scope": "test",
        "asset_admission": assets,
        "dataset_sha256": _digest_json(dataset.model_dump(mode="json")),
        "dataset_file_sha256": assets.dataset_file_sha256,
        "input_plan_file_sha256": assets.input_plan_file_sha256,
        "prompt_context_snapshot_sha256": assets.snapshot_sha256,
        "prompt_context_snapshot_file_sha256": assets.snapshot_file_sha256,
        "execution_plan": plan.execution_plan,
        "budget_report_sha256": assets.budget_report_sha256,
        "budget_report_file_sha256": assets.budget_report_file_sha256,
        "protocol_result_sha256": "b" * 64,
        "protocol_code_sha": sha,
        "protocol_input_tokens": 0,
        "protocol_output_tokens": 0,
        "protocol_total_tokens": 0,
    }
    draft = V3DomainAdmission.model_construct(**values)
    values["experiment_id"] = _admission_identity(draft)
    return V3DomainAdmission(**values), dataset


def test_cli_reports_pending_public_ci_without_loading_environment_or_provider():
    result = run_cli(
        V3DomainGateOptions(confirm_real_call=False, preflight_only=True),
        repository_root=ROOT,
        environment_loader=lambda _root: (_ for _ in ()).throw(AssertionError()),
        provider_factory=lambda _settings: (_ for _ in ()).throw(AssertionError()),
    )

    assert isinstance(result, V3PreflightStatus)
    assert result.status == "pending_public_ci"
    assert result.external_provider_calls == 0
    assert result.held_out_executed is False


def test_cli_reports_pending_fresh_protocol_after_exact_ci_identity():
    sha = head_sha()
    result = run_cli(
        V3DomainGateOptions(
            confirm_real_call=False,
            preflight_only=True,
            implementation_sha=sha,
            public_ci_sha=sha,
            confirm_public_ci_success=True,
            protocol_result=DEFAULT_PROTOCOL_RESULT,
        ),
        repository_root=ROOT,
        environment_loader=lambda _root: (_ for _ in ()).throw(AssertionError()),
        provider_factory=lambda _settings: (_ for _ in ()).throw(AssertionError()),
    )

    assert isinstance(result, V3PreflightStatus)
    assert result.status == "pending_protocol_evidence"
    assert result.asset_admission is not None
    assert result.external_provider_calls == 0


def test_v3_gate_runs_three_cases_under_revision_cap_without_registering():
    admission_value, dataset = admission()
    provider = ScriptedProvider()
    result = run_v3_domain_gate(
        admission=admission_value,
        dataset=dataset,
        provider=provider,
        case_executor=PassingExecutor(admission_value.execution_plan),
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
        clock=lambda: 100.0,
    )

    assert isinstance(result, V3DomainGateResult)
    assert result.protocol_id == PROTOCOL_ID
    assert result.admitted is True
    assert result.domain_calls_used == 9
    assert len(provider.requests) == 9
    assert result.candidate_registered is False
    assert result.production_admitted is False
    assert all(row.observation.revision_count == 0 for row in result.cases)


def test_v3_result_is_body_free():
    admission_value, dataset = admission()
    result = run_v3_domain_gate(
        admission=admission_value,
        dataset=dataset,
        provider=ScriptedProvider(),
        case_executor=PassingExecutor(admission_value.execution_plan),
        confirm_real_call=True,
    )
    encoded = canonical_v3_result_bytes(result).decode("utf-8")
    for private in ("LanternMoss", "LANTERN_USER_DATA_317", '"content"', '"messages"', '"reasoning"', '"api_key"'):
        assert private not in encoded
