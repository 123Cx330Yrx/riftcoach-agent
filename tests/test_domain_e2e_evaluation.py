from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.domain_e2e import (
    DomainDatasetRole,
    FailureCode,
    LayerVerdict,
    evaluate_domain_candidate,
    load_domain_candidate,
    load_domain_dataset,
    validate_domain_dataset_usage,
)


DEVELOPMENT_DATASET_PATH = Path(
    "data/evaluation/domain_e2e_v1_development_cases.json"
)
DEVELOPMENT_CANDIDATE_PATH = Path(
    "data/evaluation/candidates/domain_e2e_v1_offline_baseline.json"
)
DEVELOPMENT_RESULT_PATH = Path(
    "data/evaluation/results/domain_e2e_v1_offline_baseline.json"
)


def test_development_dataset_freezes_layered_contract_and_contamination():
    dataset = load_domain_dataset(DEVELOPMENT_DATASET_PATH)

    assert dataset.dataset_id == "domain-e2e-v1-development"
    assert dataset.schema_version == "1.1"
    assert dataset.dataset_version == "1.1.0"
    assert dataset.role is DomainDatasetRole.DEVELOPMENT
    assert dataset.calibration_excluded is False
    assert dataset.contract_snapshot.skill_name == "recent-form-review"
    assert dataset.contract_snapshot.skill_version == "0.2.0"
    assert dataset.contract_snapshot.context_contract == "context-builder-v1"
    assert dataset.contract_snapshot.evaluation_contract == (
        "coach_evaluation@1.0.0"
    )
    assert dataset.contract_snapshot.prompt_context_snapshot_id == (
        "recent-form-prompt-context-v1"
    )
    assert len(
        dataset.contract_snapshot.prompt_context_snapshot_sha256
    ) == 64
    assert len(dataset.cases) == 10
    assert all(case.contamination_sources for case in dataset.cases)


def test_candidate_identity_and_case_set_match_dataset():
    dataset = load_domain_dataset(DEVELOPMENT_DATASET_PATH)
    candidate = load_domain_candidate(DEVELOPMENT_CANDIDATE_PATH)

    assert candidate.dataset_id == dataset.dataset_id
    assert candidate.dataset_version == dataset.dataset_version
    assert candidate.contract_snapshot == dataset.contract_snapshot
    assert {case.case_id for case in candidate.cases} == {
        case.case_id for case in dataset.cases
    }


def test_real_bad_case_retains_only_sanitized_recorded_observation():
    candidate = load_domain_candidate(DEVELOPMENT_CANDIDATE_PATH)
    case = next(
        row for row in candidate.cases
        if row.case_id == "provider_response_unavailable_real_5d6b"
    )

    assert case.provider_calls == 1
    assert case.normalized_response_count == 0
    assert case.agent_status is None
    assert case.terminal_status == "degraded"
    assert case.input_tokens is None
    assert case.output_tokens is None
    assert case.estimated_cost is None
    assert case.provenance_sha256 == (
        "eae3054c5324dcd25d41f8387c8fb66112532231493596b1b51d08cb856846d4"
    )
    serialized = case.model_dump_json()
    for forbidden in (
        "prompt",
        "request_id",
        "exception",
        "api_key",
        "model_content",
        "reasoning_content",
    ):
        assert forbidden not in serialized.casefold()


def test_layered_baseline_classifies_each_known_failure():
    dataset = load_domain_dataset(DEVELOPMENT_DATASET_PATH)
    candidate = load_domain_candidate(DEVELOPMENT_CANDIDATE_PATH)

    result = evaluate_domain_candidate(dataset, candidate)

    assert result.case_count == 10
    assert result.task_outcome_accuracy == 1.0
    assert result.failure_classification_accuracy == 1.0
    assert result.unsafe_publication_rate == 0.1
    actual = {case.case_id: case for case in result.cases}
    assert actual["happy_path"].task_succeeded is True
    assert actual["happy_path"].primary_failure is None
    assert actual[
        "provider_response_unavailable_real_5d6b"
    ].primary_failure is FailureCode.PROVIDER_RESPONSE_UNAVAILABLE
    assert actual["tool_selection_missing"].primary_failure is (
        FailureCode.TOOL_SELECTION_MISSING
    )
    assert actual["tool_execution_incomplete"].primary_failure is (
        FailureCode.TOOL_EXECUTION_INCOMPLETE
    )
    assert actual["evidence_missing"].primary_failure is (
        FailureCode.EVIDENCE_MISSING
    )
    assert actual["citation_check_failed"].primary_failure is (
        FailureCode.CITATION_CHECK_FAILED
    )
    assert actual["injection_resistance_failed"].primary_failure is (
        FailureCode.INJECTION_RESISTANCE_FAILED
    )
    assert actual["quality_gate_failed"].primary_failure is (
        FailureCode.QUALITY_GATE_FAILED
    )
    unsafe = actual["unsafe_publication"]
    assert unsafe.primary_failure is FailureCode.INJECTION_RESISTANCE_FAILED
    assert FailureCode.UNSAFE_PUBLICATION in unsafe.failure_codes
    assert unsafe.layers.terminal.verdict is LayerVerdict.FAIL
    resource = actual["resource_limit_exceeded"]
    assert resource.primary_failure is FailureCode.RESOURCE_LIMIT_EXCEEDED
    assert resource.layers.resources.verdict is LayerVerdict.FAIL


def test_upstream_failure_makes_downstream_required_layers_unknown():
    result = evaluate_domain_candidate(
        load_domain_dataset(DEVELOPMENT_DATASET_PATH),
        load_domain_candidate(DEVELOPMENT_CANDIDATE_PATH),
    )
    case = next(
        row for row in result.cases
        if row.case_id == "provider_response_unavailable_real_5d6b"
    )

    assert case.layers.provider_agent.verdict is LayerVerdict.FAIL
    assert case.layers.tool.verdict is LayerVerdict.UNKNOWN
    assert case.layers.evidence.verdict is LayerVerdict.UNKNOWN
    assert case.layers.evaluation.verdict is LayerVerdict.UNKNOWN
    assert case.layers.terminal.verdict is LayerVerdict.PASS


def test_missing_resource_measurements_remain_unknown_not_zero_or_failed():
    result = evaluate_domain_candidate(
        load_domain_dataset(DEVELOPMENT_DATASET_PATH),
        load_domain_candidate(DEVELOPMENT_CANDIDATE_PATH),
    )
    case = next(row for row in result.cases if row.case_id == "happy_path")

    assert case.layers.resources.verdict is LayerVerdict.UNKNOWN
    assert FailureCode.RESOURCE_LIMIT_EXCEEDED not in case.failure_codes


def test_loader_rejects_duplicate_case_ids_and_candidate_snapshot_drift(
    tmp_path: Path,
):
    dataset_payload = json.loads(
        DEVELOPMENT_DATASET_PATH.read_text(encoding="utf-8")
    )
    dataset_payload["cases"].append(dataset_payload["cases"][0])
    dataset_payload["case_count"] += 1
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(json.dumps(dataset_payload), encoding="utf-8")

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        load_domain_dataset(duplicate_path)

    candidate_payload = json.loads(
        DEVELOPMENT_CANDIDATE_PATH.read_text(encoding="utf-8")
    )
    candidate_payload["contract_snapshot"]["skill_version"] = "9.9.9"
    drift_path = tmp_path / "drift.json"
    drift_path.write_text(json.dumps(candidate_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="contract snapshot mismatch"):
        evaluate_domain_candidate(
            load_domain_dataset(DEVELOPMENT_DATASET_PATH),
            load_domain_candidate(drift_path),
        )


def test_candidate_schema_rejects_raw_prompt_or_exception_text(tmp_path: Path):
    payload = json.loads(
        DEVELOPMENT_CANDIDATE_PATH.read_text(encoding="utf-8")
    )
    payload["cases"][0]["raw_prompt"] = "untrusted prompt text"
    payload["cases"][1]["exception"] = "raw Provider exception"
    path = tmp_path / "unsafe-candidate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        load_domain_candidate(path)


def test_held_out_usage_requires_role_and_frozen_confirmation(tmp_path: Path):
    payload = json.loads(DEVELOPMENT_DATASET_PATH.read_text(encoding="utf-8"))
    payload.update(
        {
            "dataset_id": "synthetic-held-out",
            "role": "held_out",
            "calibration_excluded": True,
            "contamination_notes": [],
        }
    )
    for case in payload["cases"]:
        case["contamination_sources"] = []
    path = tmp_path / "held-out.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    dataset = load_domain_dataset(path)

    with pytest.raises(ValueError, match="role is held_out"):
        validate_domain_dataset_usage(
            dataset,
            DomainDatasetRole.DEVELOPMENT,
        )
    with pytest.raises(ValueError, match="rules are frozen"):
        validate_domain_dataset_usage(
            dataset,
            DomainDatasetRole.HELD_OUT,
        )
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )


def test_development_cli_rejects_held_out_before_writing_result(tmp_path: Path):
    payload = json.loads(DEVELOPMENT_DATASET_PATH.read_text(encoding="utf-8"))
    payload.update(
        {
            "dataset_id": "synthetic-held-out",
            "role": "held_out",
            "calibration_excluded": True,
            "contamination_notes": [],
        }
    )
    for case in payload["cases"]:
        case["contamination_sources"] = []
    dataset_path = tmp_path / "held-out.json"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")

    candidate_payload = json.loads(
        DEVELOPMENT_CANDIDATE_PATH.read_text(encoding="utf-8")
    )
    candidate_payload["dataset_id"] = "synthetic-held-out"
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate_payload), encoding="utf-8")
    output_path = tmp_path / "must-not-exist.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_domain_e2e.py",
            "--dataset",
            str(dataset_path),
            "--candidate",
            str(candidate_path),
            "--mode",
            "development",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert "role is held_out, expected development" in completed.stderr
    assert not output_path.exists()


def test_development_cli_writes_reproducible_baseline(tmp_path: Path):
    output_path = tmp_path / "baseline.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_domain_e2e.py",
            "--dataset",
            str(DEVELOPMENT_DATASET_PATH),
            "--candidate",
            str(DEVELOPMENT_CANDIDATE_PATH),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    generated = json.loads(output_path.read_text(encoding="utf-8"))
    frozen = json.loads(DEVELOPMENT_RESULT_PATH.read_text(encoding="utf-8"))
    assert generated == frozen
    assert "External Provider calls: 0" in completed.stdout
