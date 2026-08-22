from __future__ import annotations

from pathlib import Path
import json

import pytest

from app.evaluation.stage8_experiment import (
    ExperimentSplit,
    ExperimentViolation,
    HoldoutAdmission,
    ImmutableExperimentOutput,
    load_experiment_record,
    prepare_holdout_admission,
    run_stage8_experiment,
    write_experiment_record_exclusive,
)


ROOT = Path(__file__).resolve().parents[1]
CODE_SHA = "2" * 40


def _development(tmp_path: Path):
    return run_stage8_experiment(
        repository_root=ROOT,
        split=ExperimentSplit.DEVELOPMENT,
        code_sha=CODE_SHA,
        runs_root=tmp_path / "runs",
    )


def test_development_result_is_strict_round_trippable_and_immutable(
    tmp_path: Path,
) -> None:
    result = _development(tmp_path)
    output = tmp_path / "development.json"

    write_experiment_record_exclusive(output, result)

    assert load_experiment_record(output) == result
    with pytest.raises(FileExistsError):
        write_experiment_record_exclusive(output, result)


@pytest.mark.parametrize(
    ("public_sha", "confirm_ci", "confirm_holdout", "code"),
    [
        ("3" * 40, True, True, "public_ci_identity_mismatch"),
        (CODE_SHA, False, True, "public_ci_confirmation_required"),
        (CODE_SHA, True, False, "holdout_confirmation_required"),
    ],
)
def test_holdout_preflight_requires_same_successful_sha_and_explicit_confirmation(
    tmp_path: Path,
    public_sha: str,
    confirm_ci: bool,
    confirm_holdout: bool,
    code: str,
) -> None:
    development = _development(tmp_path)
    development_path = tmp_path / "development.json"
    write_experiment_record_exclusive(development_path, development)

    with pytest.raises(ExperimentViolation) as caught:
        prepare_holdout_admission(
            repository_root=ROOT,
            development_result_path=development_path,
            code_sha=CODE_SHA,
            public_ci_sha=public_sha,
            confirm_public_ci_success=confirm_ci,
            confirm_holdout=confirm_holdout,
        )

    assert caught.value.code == code


def test_holdout_preflight_binds_development_gate_cases_and_clean_sha(
    tmp_path: Path,
) -> None:
    development = _development(tmp_path)
    development_path = tmp_path / "development.json"
    write_experiment_record_exclusive(development_path, development)

    admission = prepare_holdout_admission(
        repository_root=ROOT,
        development_result_path=development_path,
        code_sha=CODE_SHA,
        public_ci_sha=CODE_SHA,
        confirm_public_ci_success=True,
        confirm_holdout=True,
    )

    assert isinstance(admission, HoldoutAdmission)
    assert admission.code_sha == CODE_SHA
    assert admission.public_ci_sha == CODE_SHA
    assert admission.development_experiment_id == development.experiment_id
    assert admission.external_io_calls == 0
    assert admission.holdout_executions == 0


def test_immutable_output_keeps_a_sentinel_on_failure_and_never_overwrites(
    tmp_path: Path,
) -> None:
    output = tmp_path / "holdout.json"
    reservation = ImmutableExperimentOutput.reserve(
        output,
        experiment_id="4" * 64,
    )
    reservation.abandon()

    assert output.exists()
    assert output.read_bytes() == b""
    with pytest.raises(FileExistsError):
        ImmutableExperimentOutput.reserve(output, experiment_id="4" * 64)


def test_holdout_admission_identity_cannot_be_used_with_another_code_sha(
    tmp_path: Path,
) -> None:
    development = _development(tmp_path)
    development_path = tmp_path / "development.json"
    write_experiment_record_exclusive(development_path, development)
    admission = prepare_holdout_admission(
        repository_root=ROOT,
        development_result_path=development_path,
        code_sha=CODE_SHA,
        public_ci_sha=CODE_SHA,
        confirm_public_ci_success=True,
        confirm_holdout=True,
    )

    with pytest.raises(ExperimentViolation) as caught:
        run_stage8_experiment(
            repository_root=ROOT,
            split=ExperimentSplit.HOLDOUT,
            code_sha="5" * 40,
            public_ci_sha="5" * 40,
            admission=admission,
            runs_root=tmp_path / "holdout-runs",
        )

    assert caught.value.code == "holdout_admission_identity_drift"


def test_result_loader_recomputes_metrics_and_rejects_tampering(tmp_path: Path) -> None:
    development = _development(tmp_path)
    output = tmp_path / "development.json"
    write_experiment_record_exclusive(output, development)
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["metrics"][2]["total_token_ratio"] = 1.0
    output.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExperimentViolation) as caught:
        load_experiment_record(output)

    assert caught.value.code == "experiment_metrics_drift"


def test_result_loader_rejects_duplicate_keys_and_role_contract_drift(
    tmp_path: Path,
) -> None:
    development = _development(tmp_path)
    duplicate = tmp_path / "duplicate.json"
    raw = development.model_dump_json(indent=2).replace(
        '  "schema_version": "1.0",',
        '  "schema_version": "1.0",\n  "schema_version": "1.0",',
        1,
    )
    duplicate.write_text(raw, encoding="utf-8")
    with pytest.raises(ExperimentViolation) as duplicate_error:
        load_experiment_record(duplicate)
    assert duplicate_error.value.code == "experiment_result_invalid"

    role_drift = tmp_path / "role-drift.json"
    payload = development.model_dump(mode="json")
    payload["cases"][0]["role_contexts"][0]["allowed_tools"] = [
        "knowledge.search"
    ]
    role_drift.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ExperimentViolation) as role_error:
        load_experiment_record(role_drift)
    assert role_error.value.code == "experiment_role_contract_drift"


def test_holdout_runner_rejects_tampered_admission_id_before_cases(
    tmp_path: Path,
) -> None:
    development = _development(tmp_path)
    development_path = tmp_path / "development.json"
    write_experiment_record_exclusive(development_path, development)
    admission = prepare_holdout_admission(
        repository_root=ROOT,
        development_result_path=development_path,
        code_sha=CODE_SHA,
        public_ci_sha=CODE_SHA,
        confirm_public_ci_success=True,
        confirm_holdout=True,
    ).model_copy(update={"admission_id": "f" * 64})

    with pytest.raises(ExperimentViolation) as caught:
        run_stage8_experiment(
            repository_root=ROOT,
            split=ExperimentSplit.HOLDOUT,
            code_sha=CODE_SHA,
            public_ci_sha=CODE_SHA,
            admission=admission,
            runs_root=tmp_path / "must-remain-empty",
        )

    assert caught.value.code == "holdout_admission_identity_drift"
    assert not (tmp_path / "must-remain-empty").exists()
