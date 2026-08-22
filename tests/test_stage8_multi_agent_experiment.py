from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from importlib import import_module

import pytest

from app.evaluation.stage8_experiment import (
    HoldoutAdmission,
    ExperimentSplit,
    ExperimentViolation,
    StrategyId,
    build_experiment_id,
    build_holdout_admission_id,
    run_stage8_experiment,
)
from app.evaluation.stage8_adoption import load_adoption_gate
from app.evaluation.stage8_adoption.models import CaseSplit, ExpectedTerminal


ROOT = Path(__file__).resolve().parents[1]
CODE_SHA = "1" * 40


def _run(tmp_path: Path):
    return run_stage8_experiment(
        repository_root=ROOT,
        split=ExperimentSplit.DEVELOPMENT,
        code_sha=CODE_SHA,
        runs_root=tmp_path / "runs",
    )


def test_development_executes_three_fair_paths_through_real_harness(
    tmp_path: Path,
) -> None:
    record = _run(tmp_path)

    assert record.split is ExperimentSplit.DEVELOPMENT
    assert record.gate_digest == (
        "88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6"
    )
    assert record.case_set_sha256 == (
        "d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e"
    )
    assert record.external_io_calls == 0
    assert record.holdout_executions == 0
    assert len(record.cases) == 9
    assert {row.strategy_id for row in record.cases} == set(StrategyId)
    assert {row.case_id for row in record.cases} == {
        "dev-independent-evidence-latency",
        "dev-meta-schema-drift",
        "dev-meta-instruction-payload",
    }
    assert all(row.terminal_matches_expected for row in record.cases)
    assert all(row.hard_gates.total == 0 for row in record.cases)
    assert all(row.harness_status in {"published", "degraded"} for row in record.cases)
    assert len(list((tmp_path / "runs").glob("*/manifest.json"))) == 9


def test_normal_case_publishes_digest_bound_knowledge_and_meta_artifacts(
    tmp_path: Path,
) -> None:
    record = _run(tmp_path)
    rows = [
        row
        for row in record.cases
        if row.case_id == "dev-independent-evidence-latency"
    ]

    assert {row.terminal_status for row in rows} == {"published"}
    assert all(row.final_artifact_sha256 is not None for row in rows)
    assert all(
        {artifact.artifact_kind for artifact in row.preserved_artifacts}
        == {"knowledge_evidence", "meta_evidence"}
        for row in rows
    )
    assert all(
        artifact.payload_sha256 != artifact.provenance_sha256
        for row in rows
        for artifact in row.preserved_artifacts
    )


def test_meta_faults_preserve_only_knowledge_and_harness_degrades_safely(
    tmp_path: Path,
) -> None:
    record = _run(tmp_path)
    fault_rows = [
        row
        for row in record.cases
        if row.case_id != "dev-independent-evidence-latency"
    ]

    assert len(fault_rows) == 6
    assert {row.terminal_status for row in fault_rows} == {"degraded"}
    assert {row.error_code for row in fault_rows} == {
        "meta_instruction_payload_rejected",
        "meta_schema_drift",
    }
    assert all(
        tuple(item.artifact_kind for item in row.preserved_artifacts)
        == ("knowledge_evidence",)
        for row in fault_rows
    )
    assert all(row.harness_decision == "deterministic_fallback" for row in fault_rows)


def test_role_isolated_candidate_has_exact_independent_contexts_and_permissions(
    tmp_path: Path,
) -> None:
    record = _run(tmp_path)
    candidate = next(
        row
        for row in record.cases
        if row.case_id == "dev-independent-evidence-latency"
        and row.strategy_id is StrategyId.ROLE_ISOLATED_MULTI_AGENT
    )

    assert candidate.independent_contexts is True
    assert {role.role_id: role.allowed_tools for role in candidate.role_contexts} == {
        "knowledge_agent": ("knowledge.search",),
        "meta_agent": ("opgg.lane_meta",),
        "coach_agent": (),
    }
    assert len({role.context_sha256 for role in candidate.role_contexts}) == 3
    assert all(role.can_publish is False for role in candidate.role_contexts)


def test_development_metrics_meet_cost_and_baseline_latency_gates(
    tmp_path: Path,
) -> None:
    record = _run(tmp_path)
    metrics = {row.strategy_id: row for row in record.metrics}
    baseline = metrics[StrategyId.SERIAL]
    comparator = metrics[StrategyId.BOUNDED_PARALLEL]
    candidate = metrics[StrategyId.ROLE_ISOLATED_MULTI_AGENT]

    assert baseline.modeled_latency_units == 610
    assert comparator.modeled_latency_units == 415
    assert candidate.modeled_latency_units == 445
    assert comparator.modeled_latency_improvement_ratio == pytest.approx(195 / 610)
    assert candidate.modeled_latency_improvement_ratio == pytest.approx(165 / 610)
    assert candidate.total_token_ratio == pytest.approx(1.45)
    assert candidate.max_extra_provider_calls_per_case == 2
    assert candidate.harness_decision_match_rate == 1.0
    assert candidate.safe_degraded_rate == 1.0
    assert record.verdict == "eligible_for_holdout"
    assert record.reason_codes == ("development_thresholds_passed",)


def test_public_record_is_body_free_and_deterministic(tmp_path: Path) -> None:
    first = _run(tmp_path / "first")
    second = _run(tmp_path / "second")

    assert first == second
    public = first.model_dump_json()
    for forbidden in (
        "scenario",
        "Example#TEST",
        "分析一下我最近",
        "视野分只能",
        "instruction-like",
        str(tmp_path),
        "traceback",
    ):
        assert forbidden not in public


def test_runner_refuses_holdout_without_a_sha_bound_admission(tmp_path: Path) -> None:
    with pytest.raises(ExperimentViolation) as caught:
        run_stage8_experiment(
            repository_root=ROOT,
            split=ExperimentSplit.HOLDOUT,
            code_sha=CODE_SHA,
            runs_root=tmp_path / "runs",
        )

    assert caught.value.code == "holdout_admission_required"


def test_holdout_execution_path_is_tested_only_with_synthetic_non_holdout_cases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise production holdout wiring without consuming frozen holdout rows."""

    loaded = load_adoption_gate(
        ROOT / "data/evaluation/stage8/advanced_adoption_gate_v1.json",
        ROOT / "data/evaluation/stage8/advanced_adoption_cases_v1.json",
    )
    development = [
        row for row in loaded.case_set.cases if row.split is CaseSplit.DEVELOPMENT
    ]
    synthetic = (
        development[0].model_copy(
            update={
                "case_id": "synthetic-holdout-normal",
                "split": CaseSplit.HOLDOUT,
                "calibration_excluded": True,
            }
        ),
        development[1].model_copy(
            update={
                "case_id": "synthetic-holdout-timeout",
                "split": CaseSplit.HOLDOUT,
                "calibration_excluded": True,
                "fault": "meta_timeout",
            }
        ),
        development[2].model_copy(
            update={
                "case_id": "synthetic-holdout-tool-probe",
                "split": CaseSplit.HOLDOUT,
                "calibration_excluded": True,
                "fault": "cross_role_tool_probe",
                "expected_terminal": ExpectedTerminal.FAILED,
                "expected_preserved_artifacts": (),
                "expected_error_code": "role_tool_not_allowed",
            }
        ),
    )
    synthetic_loaded = replace(
        loaded,
        case_set=loaded.case_set.model_copy(
            update={"cases": tuple(development) + synthetic}
        ),
    )
    runner_module = import_module("app.evaluation.stage8_experiment.runner")
    monkeypatch.setattr(
        runner_module,
        "load_adoption_gate",
        lambda gate_path, cases_path: synthetic_loaded,
    )
    record_gate_digest = (
        "88f879f09480fbbb5776aae2d6d0057af9b37f0159784430d3bcca167cc09fc6"
    )
    record_case_sha = (
        "d53fb864e0c9ddc4b54f483da9025ac68b145fde8b4393645e977af4e60aad4e"
    )
    holdout_id = build_experiment_id(
        split=ExperimentSplit.HOLDOUT,
        code_sha=CODE_SHA,
        public_ci_sha=CODE_SHA,
        gate_digest=record_gate_digest,
        case_set_sha256=record_case_sha,
    )
    development_experiment_id = "9" * 64
    admission = HoldoutAdmission(
        admission_id=build_holdout_admission_id(
            development_experiment_id=development_experiment_id,
            code_sha=CODE_SHA,
            public_ci_sha=CODE_SHA,
            gate_digest=record_gate_digest,
            case_set_sha256=record_case_sha,
        ),
        holdout_experiment_id=holdout_id,
        development_experiment_id=development_experiment_id,
        code_sha=CODE_SHA,
        public_ci_sha=CODE_SHA,
        gate_digest=record_gate_digest,
        case_set_sha256=record_case_sha,
    )

    record = run_stage8_experiment(
        repository_root=ROOT,
        split=ExperimentSplit.HOLDOUT,
        code_sha=CODE_SHA,
        public_ci_sha=CODE_SHA,
        admission=admission,
        runs_root=tmp_path / "synthetic-holdout-runs",
    )

    assert record.holdout_executions == 1
    assert record.external_io_calls == 0
    assert record.verdict == "reject_multi_agent"
    assert "no_incremental_benefit_over_parallel" in record.reason_codes
    assert {row.error_code for row in record.cases if row.terminal_status == "failed"} == {
        "role_tool_not_allowed"
    }
