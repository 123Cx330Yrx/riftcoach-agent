from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.evaluation.stage8_adoption import (
    AdoptionGateError,
    CandidateOutcome,
    evaluate_adoption_gate,
    load_adoption_gate,
)


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/evaluation/stage8/advanced_adoption_gate_v1.json"
CASES = ROOT / "data/evaluation/stage8/advanced_adoption_cases_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_mutated_assets(
    tmp_path: Path,
    *,
    mutate_gate=None,
    mutate_cases=None,
) -> tuple[Path, Path]:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if mutate_cases is not None:
        mutate_cases(cases)
    case_path = tmp_path / "cases.json"
    case_path.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gate["case_set"]["sha256"] = _sha256(case_path)
    if mutate_gate is not None:
        mutate_gate(gate)
    gate_path = tmp_path / "gate.json"
    gate_path.write_text(
        json.dumps(gate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return gate_path, case_path


def _candidate(payload: dict, candidate_id: str) -> dict:
    return next(
        item for item in payload["candidates"] if item["candidate_id"] == candidate_id
    )


def test_frozen_gate_selects_multi_agent_with_parallel_comparator_body_free() -> None:
    loaded = load_adoption_gate(GATE, CASES)
    decision = evaluate_adoption_gate(loaded)
    outcomes = {item.candidate_id: item.outcome for item in decision.candidates}

    assert loaded.case_set.case_set_id == "stage8-advanced-adoption-cases-v1"
    assert {case.split.value for case in loaded.case_set.cases} == {
        "development",
        "holdout",
    }
    assert loaded.case_set.calibration_policy.holdout_calibration_excluded is True
    assert loaded.gate.case_set.sha256 == _sha256(CASES)
    assert decision.baseline_id == "single-runtime-serial-v1"
    assert decision.primary_candidate_id == "role-isolated-multi-agent-v1"
    assert decision.comparator_ids == ("bounded-parallel-evidence-v1",)
    assert outcomes == {
        "single-runtime-serial-v1": CandidateOutcome.BASELINE,
        "bounded-parallel-evidence-v1": CandidateOutcome.CANDIDATE,
        "role-isolated-multi-agent-v1": CandidateOutcome.CANDIDATE,
        "third-party-dag-runtime-v1": CandidateOutcome.DEFERRED,
        "agentic-retrieval-v1": CandidateOutcome.DEFERRED,
    }
    assert decision.external_io_calls == 0
    assert decision.holdout_executions == 0
    assert decision.gate_digest == (
        "88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6"
    )
    assert decision == evaluate_adoption_gate(load_adoption_gate(GATE, CASES))

    public = decision.model_dump_json()
    for forbidden in (
        "scenario",
        "instruction-like",
        "player_summary_demo",
        "deterministic_report_demo",
        str(ROOT),
    ):
        assert forbidden not in public


def test_case_set_identity_drift_fails_closed(tmp_path: Path) -> None:
    gate_path, case_path = _write_mutated_assets(tmp_path)
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["case_set"]["sha256"] = "0" * 64
    gate_path.write_text(json.dumps(gate), encoding="utf-8")

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "case_set_identity_drift"
    assert str(caught.value) == "case_set_identity_drift"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("external_io_budget", 1, "real_external_io_requested"),
        ("retry_budget", 1, "retry_budget_forbidden"),
        ("holdout_max_executions", 2, "holdout_execution_budget_invalid"),
        ("result_overwrite_allowed", True, "result_overwrite_requested"),
    ],
)
def test_comparison_contract_forbids_io_retries_and_mutable_holdout(
    tmp_path: Path,
    field: str,
    value: object,
    code: str,
) -> None:
    def mutate(gate: dict) -> None:
        gate["comparison_contract"][field] = value

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == code


def test_role_tool_permission_overlap_is_rejected(tmp_path: Path) -> None:
    def mutate(gate: dict) -> None:
        candidate = _candidate(gate, "role-isolated-multi-agent-v1")
        candidate["roles"][1]["allowed_tools"].append("knowledge.search")

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "role_tool_permission_overlap"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("agent_can_publish", "unsafe_publication"),
        ("coach_has_tool", "coach_tool_permission_forbidden"),
        ("shared_multi_agent_context", "independent_context_required"),
    ],
)
def test_multi_agent_roles_cannot_publish_widen_tools_or_share_context(
    tmp_path: Path,
    mutation: str,
    code: str,
) -> None:
    def mutate(gate: dict) -> None:
        candidate = _candidate(gate, "role-isolated-multi-agent-v1")
        if mutation == "agent_can_publish":
            candidate["roles"][0]["can_publish"] = True
        elif mutation == "coach_has_tool":
            candidate["roles"][2]["allowed_tools"] = ["knowledge.search"]
        else:
            candidate["roles"][1]["independent_context"] = False

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == code


def test_development_and_calibration_excluded_holdout_are_both_required(
    tmp_path: Path,
) -> None:
    def mutate_cases(cases: dict) -> None:
        cases["cases"] = [
            item for item in cases["cases"] if item["split"] == "development"
        ]

    gate_path, case_path = _write_mutated_assets(
        tmp_path,
        mutate_cases=mutate_cases,
    )

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "holdout_cases_missing"


def test_all_stop_conditions_and_hard_metrics_are_required(tmp_path: Path) -> None:
    def mutate(gate: dict) -> None:
        gate["stop_condition_codes"].remove("no_incremental_benefit_over_parallel")
        gate["hard_gate_metrics"].remove("unsafe_publications")

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code in {
        "hard_gate_metrics_incomplete",
        "stop_conditions_incomplete",
    }


def test_primary_candidate_must_remain_evaluable_and_dependency_free(
    tmp_path: Path,
) -> None:
    def mutate(gate: dict) -> None:
        candidate = _candidate(gate, "role-isolated-multi-agent-v1")
        candidate["disposition"] = "deferred"
        candidate["deferred_reason_codes"] = ["manual_defer"]
        candidate["production_dependency_allowed"] = True

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code in {
        "primary_candidate_not_evaluable",
        "production_dependency_forbidden",
    }


def test_deferred_candidates_need_explicit_reasons(tmp_path: Path) -> None:
    def mutate(gate: dict) -> None:
        candidate = _candidate(gate, "agentic-retrieval-v1")
        candidate["deferred_reason_codes"] = []

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "deferred_reason_required"


def test_gate_json_rejects_duplicate_object_keys(tmp_path: Path) -> None:
    duplicate = GATE.read_text(encoding="utf-8").replace(
        '  "schema_version": "1.0",',
        '  "schema_version": "1.0",\n  "schema_version": "1.0",',
        1,
    )
    gate_path = tmp_path / "duplicate-gate.json"
    gate_path.write_text(duplicate, encoding="utf-8")

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, CASES)

    assert caught.value.code == "adoption_gate_json_invalid"


def test_serial_baseline_kind_is_immutable(tmp_path: Path) -> None:
    def mutate(gate: dict) -> None:
        baseline = _candidate(gate, "single-runtime-serial-v1")
        baseline["kind"] = "bounded_parallel"

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "baseline_kind_invalid"


def test_unregistered_active_candidate_is_rejected(tmp_path: Path) -> None:
    def mutate(gate: dict) -> None:
        extra = deepcopy(_candidate(gate, "bounded-parallel-evidence-v1"))
        extra["candidate_id"] = "unregistered-parallel-v1"
        gate["candidates"].append(extra)

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "active_candidate_identity_invalid"


def test_second_baseline_is_rejected(tmp_path: Path) -> None:
    def mutate(gate: dict) -> None:
        extra = deepcopy(_candidate(gate, "single-runtime-serial-v1"))
        extra["candidate_id"] = "second-serial-baseline-v1"
        gate["candidates"].append(extra)

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "baseline_identity_invalid"


@pytest.mark.parametrize(
    ("candidate_id", "role_index"),
    [
        ("single-runtime-serial-v1", 0),
        ("bounded-parallel-evidence-v1", 1),
    ],
)
def test_baseline_and_comparator_role_contracts_are_exact(
    tmp_path: Path,
    candidate_id: str,
    role_index: int,
) -> None:
    def mutate(gate: dict) -> None:
        candidate = _candidate(gate, candidate_id)
        candidate["roles"][role_index]["context_scopes"].append("unregistered_scope")

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "candidate_role_contract_invalid"


@pytest.mark.parametrize(
    "mutation",
    ["role_id", "tool_assignment", "context_scope"],
)
def test_multi_agent_role_contract_is_exact(tmp_path: Path, mutation: str) -> None:
    def mutate(gate: dict) -> None:
        candidate = _candidate(gate, "role-isolated-multi-agent-v1")
        if mutation == "role_id":
            candidate["roles"][0]["role_id"] = "knowledge_agent_alt"
        elif mutation == "tool_assignment":
            candidate["roles"][0]["allowed_tools"] = ["opgg.lane_meta"]
            candidate["roles"][1]["allowed_tools"] = ["knowledge.search"]
        else:
            candidate["roles"][1]["context_scopes"].append("user_goal")

    gate_path, case_path = _write_mutated_assets(tmp_path, mutate_gate=mutate)

    with pytest.raises(AdoptionGateError) as caught:
        load_adoption_gate(gate_path, case_path)

    assert caught.value.code == "multi_agent_role_contract_invalid"
