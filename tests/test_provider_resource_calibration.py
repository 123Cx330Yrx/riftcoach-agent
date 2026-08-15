from __future__ import annotations

import json
import inspect
import tempfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from app.evaluation.provider_adoption import ExperimentFailureCode
from app.evaluation.provider_resource_calibration import (
    CALIBRATION_STAGES,
    CalibrationIncompleteError,
    CalibrationSimulationResult,
    CalibrationStage,
    ResourceCalibrationUsageObservation,
    ResourceCalibrationRequestSnapshot,
    capture_resource_calibration_requests,
    deepseek_resource_calibration_policy,
    derive_v3_resource_budget,
    load_resource_calibration_profiles,
    prepare_resource_calibration_admission,
    simulate_resource_calibration,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderTimeoutError
from app.providers.models import ChatRequest, ChatResponse, TokenUsage


ROOT = Path(__file__).resolve().parents[1]
PROFILES = (
    ROOT
    / "data/evaluation/deepseek_v4_pro_resource_calibration_development_profiles.json"
)
V2_PROTECTED = (
    ROOT / "data/evaluation/domain_e2e_v2_secure_held_out_cases.json",
    ROOT / "data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json",
    ROOT
    / "data/evaluation/results/provider_capabilities/deepseek_v4_pro_domain_adoption_v2.json",
)
REQUEST_SNAPSHOT = (
    ROOT
    / "data/evaluation/contracts/deepseek_v4_pro_resource_calibration_requests_v1.json"
)


def loaded_profiles():
    return load_resource_calibration_profiles(
        PROFILES,
        project_root=ROOT,
        protected_paths=V2_PROTECTED,
    )


@dataclass
class OfflineFakeCalibrationProvider:
    usages: tuple[tuple[int, int], ...]
    fail_at: int | None = None
    is_offline_calibration_fake: bool = True
    provider_name: str = "deepseek"
    model_name: str = "deepseek-v4-pro"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
        parallel_tool_calls=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        ordinal = len(self.requests)
        if self.fail_at == ordinal:
            raise ProviderTimeoutError(
                provider=self.provider_name,
                code="timeout",
            )
        input_tokens, output_tokens = self.usages[ordinal - 1]
        return ChatResponse(
            content="offline calibration response",
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            request_id=f"raw-fake-request-{ordinal}",
        )


class StepClock:
    def __init__(self, step_s: float = 0.1) -> None:
        self.value = 0.0
        self.step_s = step_s

    def __call__(self) -> float:
        current = self.value
        self.value += self.step_s
        return current


def test_development_profiles_are_new_bounded_and_quality_excluded():
    loaded = loaded_profiles()

    assert loaded.artifact.role == "development"
    assert loaded.artifact.quality_admission_excluded is True
    assert tuple(row.profile_id for row in loaded.profiles) == (
        "baseline",
        "ceiling",
    )
    assert loaded.artifact.required_stages == CALIBRATION_STAGES
    assert len(loaded.profiles[0].summary["matches"]) == 3
    assert len(loaded.profiles[1].summary["matches"]) == 10
    assert len(loaded.profiles[0].profile.tool_queries) == 1
    assert len(loaded.profiles[1].profile.tool_queries) == 3


def test_loader_rejects_v2_fixture_digest_reuse(tmp_path: Path):
    payload = json.loads(PROFILES.read_text(encoding="utf-8"))
    v2_plan = json.loads(V2_PROTECTED[1].read_text(encoding="utf-8"))
    payload["profiles"][0]["player_summary"]["sha256"] = v2_plan[
        "player_summary"
    ]["sha256"]
    mutated = tmp_path / "profiles.json"
    mutated.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="protected V2 content"):
        load_resource_calibration_profiles(
            mutated,
            project_root=ROOT,
            protected_paths=V2_PROTECTED,
        )


def test_loader_rejects_v2_case_body_reuse(tmp_path: Path):
    payload = json.loads(PROFILES.read_text(encoding="utf-8"))
    v2_dataset = json.loads(V2_PROTECTED[0].read_text(encoding="utf-8"))
    payload["profiles"][0]["case_id"] = v2_dataset["cases"][0]["case_id"]
    mutated = tmp_path / "profiles.json"
    mutated.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="protected V2 content"):
        load_resource_calibration_profiles(
            mutated,
            project_root=ROOT,
            protected_paths=V2_PROTECTED,
        )


def test_capture_uses_production_chain_and_exposes_only_body_free_envelopes():
    loaded = loaded_profiles()
    with tempfile.TemporaryDirectory() as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=ROOT,
            runs_root=directory,
        )

    assert len(frozen.requests) == 8
    assert tuple(row.stage for row in frozen.requests[:4]) == CALIBRATION_STAGES
    assert tuple(row.stage for row in frozen.requests[4:]) == CALIBRATION_STAGES
    assert all(row.request.max_tokens is None for row in frozen.requests)
    assert frozen.snapshot.request_count == 8
    assert frozen.snapshot.quality_admission_excluded is True
    assert frozen.snapshot.envelopes[-4].local_context_units >= 12000
    assert frozen.snapshot.envelopes[-3].local_context_units <= 16000
    assert (
        frozen.snapshot.envelopes[-3].local_context_units
        > frozen.snapshot.envelopes[-4].local_context_units
    )
    assert len(frozen.snapshot.envelopes[-4].tool_names) == 1
    ceiling_tool_message = frozen.requests[5].request.messages[-4]
    assert ceiling_tool_message.role.value == "assistant"
    assert len(ceiling_tool_message.tool_calls) == 3
    public_snapshot = ResourceCalibrationRequestSnapshot.model_validate_json(
        REQUEST_SNAPSHOT.read_bytes()
    )
    assert public_snapshot == frozen.snapshot

    public_json = frozen.snapshot.model_dump_json()
    for profile in loaded.artifact.profiles:
        assert profile.user_utterance not in public_json
        assert profile.draft_text not in public_json
        assert profile.invalid_evaluation_text not in public_json
        for query in profile.tool_queries:
            assert query not in public_json
    assert "raw-fake-request" not in public_json


def test_fake_replay_completes_exactly_eight_calls_with_64_output_cap():
    loaded = loaded_profiles()
    with tempfile.TemporaryDirectory() as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=ROOT,
            runs_root=directory,
        )
    usages = (
        (1200, 10),
        (1700, 12),
        (1300, 10),
        (700, 8),
        (1800, 12),
        (2200, 14),
        (1600, 11),
        (900, 9),
    )
    provider = OfflineFakeCalibrationProvider(usages=usages)

    result = simulate_resource_calibration(
        frozen,
        provider=provider,
        clock=StepClock(),
    )

    assert result.status == "completed"
    assert result.replay_calls_used == 8
    assert result.responses_completed == 8
    assert result.external_provider_calls == 0
    assert result.quality_admission_excluded is True
    assert len(result.observations) == 8
    assert all(request.max_tokens == 64 for request in provider.requests)
    result_json = result.model_dump_json()
    assert "raw-fake-request" not in result_json
    assert "offline calibration response" not in result_json


def test_fake_replay_stops_on_first_provider_error():
    loaded = loaded_profiles()
    with tempfile.TemporaryDirectory() as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=ROOT,
            runs_root=directory,
        )
    provider = OfflineFakeCalibrationProvider(
        usages=((100, 1),) * 8,
        fail_at=3,
    )

    result = simulate_resource_calibration(
        frozen,
        provider=provider,
        clock=StepClock(),
    )

    assert result.status == "stopped"
    assert result.failure_code is ExperimentFailureCode.PROVIDER_TIMEOUT
    assert result.replay_calls_used == 3
    assert result.responses_completed == 2
    assert len(provider.requests) == 3


def test_fake_replay_rejects_real_provider_surface_and_output_overrun():
    loaded = loaded_profiles()
    with tempfile.TemporaryDirectory() as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=ROOT,
            runs_root=directory,
        )
    unmarked = OfflineFakeCalibrationProvider(usages=((100, 1),) * 8)
    unmarked.is_offline_calibration_fake = False
    with pytest.raises(ValueError, match="explicit fake Provider"):
        simulate_resource_calibration(
            frozen,
            provider=unmarked,
            clock=StepClock(),
        )

    overrun = OfflineFakeCalibrationProvider(
        usages=((100, 65),) + ((100, 1),) * 7,
    )
    result = simulate_resource_calibration(
        frozen,
        provider=overrun,
        clock=StepClock(),
    )
    assert result.status == "stopped"
    assert result.failure_code is ExperimentFailureCode.TOKEN_BUDGET_EXHAUSTED
    assert result.replay_calls_used == 1
    assert result.responses_completed == 0


def completed_result(
    *,
    baseline_inputs=(1200, 1700, 1300, 700),
    ceiling_inputs=(1800, 2200, 1600, 900),
    baseline_latencies=(1000, 1000, 1000, 1000),
    ceiling_latencies=(2000, 2500, 1500, 1000),
) -> CalibrationSimulationResult:
    observations = []
    ordinal = 0
    for profile_id, inputs, latencies in (
        ("baseline", baseline_inputs, baseline_latencies),
        ("ceiling", ceiling_inputs, ceiling_latencies),
    ):
        for stage, input_tokens, latency_ms in zip(
            CALIBRATION_STAGES,
            inputs,
            latencies,
            strict=True,
        ):
            ordinal += 1
            observations.append(
                ResourceCalibrationUsageObservation(
                    ordinal=ordinal,
                    profile_id=profile_id,
                    stage=stage,
                    provider_id="deepseek",
                    requested_model="deepseek-v4-pro",
                    resolved_model="deepseek-v4-pro",
                    input_tokens=input_tokens,
                    output_tokens=10,
                    latency_ms=latency_ms,
                    finish_reason="stop",
                    request_id_sha256=f"{ordinal:064x}",
                )
            )
    policy = deepseek_resource_calibration_policy()
    total_input = sum(row.input_tokens for row in observations)
    total_output = sum(row.output_tokens for row in observations)
    return CalibrationSimulationResult.model_validate(
        {
            "status": "completed",
            "provider_id": policy.provider_id,
            "requested_model": policy.model,
            "request_set_sha256": "a" * 64,
            "expected_calls": 8,
            "replay_calls_used": 8,
            "responses_completed": 8,
            "observations": [row.model_dump(mode="json") for row in observations],
            "ledger": {
                "provider_id": policy.provider_id,
                "model": policy.model,
                "currency": policy.currency,
                "calls_used": 8,
                "max_calls": 8,
                "scope_calls": [{"scope": "calibration", "calls_used": 8, "max_calls": 8}],
                "scope_tokens": [{"scope": "calibration", "input_tokens": total_input, "output_tokens": total_output, "total_tokens": total_input + total_output, "max_observed_tokens": 64000}],
                "case_resources": [],
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "max_observed_tokens": 64000,
                "estimated_cost": "0.01",
                "max_estimated_cost": "0.10",
                "latency_ms": sum(row.latency_ms for row in observations),
                "stop_code": None
            },
            "failure_code": None,
            "external_provider_calls": 0,
            "quality_admission_excluded": True
        }
    )


def test_budget_derivation_uses_stage_max_margin_and_upward_rounding():
    decision = derive_v3_resource_budget(completed_result())

    assert tuple(row.input_ceiling for row in decision.stage_budgets) == (
        2304,
        2816,
        2048,
        1280,
    )
    assert decision.case_input_ceiling == 8448
    assert decision.case_output_ceiling == 4096
    assert decision.case_token_limit == 13312
    assert decision.domain_token_limit == 39936
    assert decision.global_token_limit == 41364
    assert decision.global_cost_ceiling == Decimal("0.09")
    assert decision.agent_latency_with_margin_ms == 5625
    assert decision.case_latency_limit_ms == 10000
    assert decision.v3_gate_creation_allowed is True


def test_incomplete_calibration_cannot_derive_budget():
    result = completed_result().model_copy(
        update={
            "status": "stopped",
            "responses_completed": 7,
            "observations": completed_result().observations[:-1],
            "failure_code": ExperimentFailureCode.PROVIDER_TIMEOUT,
        }
    )
    with pytest.raises(CalibrationIncompleteError):
        derive_v3_resource_budget(result)


def test_budget_derivation_rejects_cost_and_agent_deadline_overruns():
    cost = derive_v3_resource_budget(
        completed_result(
            baseline_inputs=(3000, 3500, 2500, 1200),
            ceiling_inputs=(4000, 4500, 3500, 1800),
        )
    )
    assert cost.global_cost_ceiling > Decimal("0.10")
    assert cost.v3_gate_creation_allowed is False
    assert "cost_ceiling_exceeded" in cost.rejection_reasons

    deadline = derive_v3_resource_budget(
        completed_result(
            baseline_latencies=(13000, 13000, 1000, 1000),
            ceiling_latencies=(13000, 13000, 1000, 1000),
        )
    )
    assert deadline.agent_latency_with_margin_ms == 32500
    assert "skill_agent_deadline_unreachable" in deadline.rejection_reasons


def test_no_io_admission_requires_exact_public_ci_sha():
    loaded = loaded_profiles()
    with tempfile.TemporaryDirectory() as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=ROOT,
            runs_root=directory,
        )

    report = prepare_resource_calibration_admission(
        loaded=loaded,
        frozen_requests=frozen,
        code_sha="b" * 40,
        public_ci_sha="b" * 40,
        public_ci_success_confirmed=True,
    )
    assert report.external_provider_calls == 0
    assert report.held_out_created is False
    assert report.provider_construction_authorized is False
    parameters = inspect.signature(
        prepare_resource_calibration_admission
    ).parameters
    assert not {"provider", "api_key", "client", "base_url"}.intersection(
        parameters
    )

    with pytest.raises(ValueError, match="public CI SHA"):
        prepare_resource_calibration_admission(
            loaded=loaded,
            frozen_requests=frozen,
            code_sha="b" * 40,
            public_ci_sha="c" * 40,
            public_ci_success_confirmed=True,
        )
