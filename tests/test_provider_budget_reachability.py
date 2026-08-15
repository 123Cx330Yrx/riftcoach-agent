from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.provider_budget_reachability import (
    DeepSeekV2BudgetAdjudication,
    V2_RESULT_SHA256,
    adjudicate_deepseek_v2_budget_reachability,
    measure_request_envelopes,
)
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from tests.test_provider_domain_production import SafeProvider


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/domain_e2e_v2_secure_held_out_cases.json"
PLAN = ROOT / "data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json"
RESULT = ROOT / (
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_adoption_v2.json"
)
ADJUDICATION = ROOT / (
    "data/evaluation/results/budget_reachability/"
    "deepseek_v4_pro_domain_adoption_v2.json"
)


def _offline_success_envelopes():
    dataset = load_domain_dataset(DATASET)
    plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    provider = SafeProvider()
    with tempfile.TemporaryDirectory() as directory:
        observation = ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=directory,
        ).execute(
            case_id="adoption_v2_form_baseline",
            provider=provider,
        )
    assert observation.normalized_response_count == 3
    assert observation.terminal_status == "published"
    return measure_request_envelopes(tuple(provider.requests))


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


def test_real_production_path_yields_three_body_free_request_envelopes():
    envelopes = _offline_success_envelopes()

    assert tuple(row.stage for row in envelopes) == (
        "agent_initial",
        "agent_after_tool",
        "evaluation",
    )
    assert tuple(row.message_count for row in envelopes) == (2, 4, 2)
    assert tuple(row.message_roles for row in envelopes) == (
        ("system", "user"),
        ("system", "user", "assistant", "tool"),
        ("system", "user"),
    )
    assert tuple(row.local_context_units for row in envelopes) == (
        6666,
        7774,
        6266,
    )

    serialized = json.dumps(
        [row.model_dump(mode="json") for row in envelopes],
        ensure_ascii=False,
    )
    assert "MIDKING" not in serialized
    assert "USER_INJECTION" not in serialized
    assert "KNOWLEDGE_INJECTION" not in serialized


def test_v2_exact_result_proves_second_call_is_not_reachable():
    report = adjudicate_deepseek_v2_budget_reachability(
        result_path=RESULT,
        request_envelopes=_offline_success_envelopes(),
    )

    assert report.source_result_sha256 == V2_RESULT_SHA256
    assert report.provider_id == "deepseek"
    assert report.requested_model == "deepseek-v4-pro"
    assert report.case_id == "adoption_v2_form_baseline"
    assert report.observed_input_tokens == 3241
    assert report.observed_output_tokens == 199
    assert report.observed_total_tokens == 3440
    assert report.case_token_limit == 4000
    assert report.per_request_output_cap == 1024
    assert report.next_call_reserved_total == 4464
    assert report.exact_minimum_case_limit_for_next_call == 4464
    assert report.case_limit_shortfall == 464
    assert report.next_call_reachable is False
    assert report.complete_path_reachable is False


def test_length_calibration_exposes_fake_usage_but_does_not_invent_v3_budget():
    report = adjudicate_deepseek_v2_budget_reachability(
        result_path=RESULT,
        request_envelopes=_offline_success_envelopes(),
    )
    projection = report.length_projection

    assert projection.method == "length_calibrated_not_provider_tokenizer"
    assert projection.calibration_stage == "agent_initial"
    assert projection.calibration_local_context_units == 6666
    assert projection.calibration_actual_input_tokens == 3241
    assert tuple(row.projected_input_tokens for row in projection.stages) == (
        3241,
        3780,
        3047,
    )
    assert projection.projected_input_tokens_total == 10068
    assert projection.known_output_tokens == 199
    assert projection.projected_tokens_before_future_outputs == 10267
    assert projection.exact_provider_token_count is False

    assert report.complete_path_exact_token_requirement is None
    assert report.recommended_v3_case_token_limit is None
    assert report.decision == "new_budget_design_required_before_v3_io"
    assert report.external_provider_calls == 0


def test_v2_adjudication_rejects_any_result_byte_drift(tmp_path):
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    payload["admitted"] = True
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256"):
        adjudicate_deepseek_v2_budget_reachability(
            result_path=tampered,
            request_envelopes=_offline_success_envelopes(),
        )


def test_public_adjudication_contract_forbids_sensitive_or_unknown_fields():
    report = adjudicate_deepseek_v2_budget_reachability(
        result_path=RESULT,
        request_envelopes=_offline_success_envelopes(),
    )
    payload = report.model_dump(mode="json")
    keys = set(_walk_keys(payload))

    assert keys.isdisjoint(
        {"api_key", "prompt", "response", "request_id", "raw_error"}
    )
    with pytest.raises(ValidationError):
        DeepSeekV2BudgetAdjudication.model_validate(
            {**payload, "api_key": "sk-forbidden"}
        )


def test_tracked_adjudication_rebuilds_exactly_without_provider_io():
    expected = adjudicate_deepseek_v2_budget_reachability(
        result_path=RESULT,
        request_envelopes=_offline_success_envelopes(),
    )
    tracked = DeepSeekV2BudgetAdjudication.model_validate_json(
        ADJUDICATION.read_bytes()
    )

    assert tracked == expected
