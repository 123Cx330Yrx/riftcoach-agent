from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.provider_domain_experiment import DomainCaseExecutor
from app.evaluation.provider_domain_plan import (
    DomainCaseInputPlanArtifact,
    load_domain_case_input_plan,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
PLAN = ROOT / "data/evaluation/deepseek_v4_pro_domain_heldout_input_plan.json"


def test_executor_contract_is_oracle_blind():
    parameters = inspect.signature(DomainCaseExecutor.execute).parameters

    assert tuple(parameters) == ("self", "case_id", "provider")
    assert "case" not in parameters


def test_frozen_input_plan_binds_exact_bytes_cases_and_fixtures():
    dataset = load_domain_dataset(DATASET)
    loaded = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )

    raw = PLAN.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    assert loaded.execution_plan.plan_sha256 == hashlib.sha256(canonical).hexdigest()
    assert loaded.execution_plan.case_ids == tuple(
        case.case_id for case in dataset.cases
    )
    assert loaded.artifact.dataset_id == dataset.dataset_id
    assert loaded.artifact.dataset_version == dataset.dataset_version
    assert loaded.artifact.sdk_max_retries == 0
    assert loaded.artifact.max_revisions == 0
    assert loaded.player_summary_path == (
        ROOT / loaded.artifact.player_summary.relative_path
    ).resolve()
    assert loaded.deterministic_report_path == (
        ROOT / loaded.artifact.deterministic_report.relative_path
    ).resolve()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value.update(dataset_version="9.9.9"),
            "Dataset identity",
        ),
        (
            lambda value: value["cases"].reverse(),
            "case order",
        ),
        (
            lambda value: value["player_summary"].update(sha256="0" * 64),
            "fixture digest",
        ),
        (
            lambda value: value["player_summary"].update(
                relative_path="../outside.json"
            ),
            "project-relative",
        ),
    ],
)
def test_input_plan_drift_fails_before_it_can_be_admitted(
    tmp_path,
    mutation,
    message,
):
    dataset = load_domain_dataset(DATASET)
    value = json.loads(PLAN.read_text(encoding="utf-8"))
    mutation(value)
    changed = tmp_path / "plan.json"
    changed.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises((ValueError, FileNotFoundError), match=message):
        load_domain_case_input_plan(
            changed,
            project_root=ROOT,
            dataset=dataset,
        )


def test_plan_rejects_unfrozen_case_modes_and_revision_budget(tmp_path):
    dataset = load_domain_dataset(DATASET)
    value = json.loads(PLAN.read_text(encoding="utf-8"))
    value["max_revisions"] = 1
    changed = tmp_path / "plan.json"
    changed.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError):
        load_domain_case_input_plan(
            changed,
            project_root=ROOT,
            dataset=dataset,
        )


def test_v1_plan_remains_strictly_readable_without_fresh_context_fields():
    artifact = DomainCaseInputPlanArtifact.model_validate_json(PLAN.read_bytes())

    assert artifact.schema_version == "1.0"
    assert artifact.prompt_context_snapshot_id is None
    assert artifact.prompt_context_snapshot_sha256 is None
    assert artifact.case_context_commitments == ()


def _v11_plan_payload() -> dict:
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    payload.update(
        schema_version="1.1",
        plan_id="synthetic-fresh-domain-development",
        plan_version="1.1.0-dev",
        prompt_context_snapshot_id="synthetic-fresh-context-v1-1",
        prompt_context_snapshot_sha256="a" * 64,
        case_context_commitments=[
            {"case_id": row["case_id"], "context_sha256": str(index) * 64}
            for index, row in enumerate(payload["cases"], start=1)
        ],
    )
    return payload


def test_v11_plan_requires_ordered_context_commitments_for_every_case():
    artifact = DomainCaseInputPlanArtifact.model_validate(_v11_plan_payload())

    assert artifact.schema_version == "1.1"
    assert artifact.prompt_context_snapshot_id == "synthetic-fresh-context-v1-1"
    assert tuple(row.case_id for row in artifact.case_context_commitments) == tuple(
        row.case_id for row in artifact.cases
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value.pop("prompt_context_snapshot_sha256"),
            "snapshot identity",
        ),
        (
            lambda value: value.update(case_context_commitments=[]),
            "Context commitments",
        ),
        (
            lambda value: value["case_context_commitments"].reverse(),
            "case order",
        ),
        (
            lambda value: value["case_context_commitments"].__setitem__(
                1,
                value["case_context_commitments"][0],
            ),
            "case order",
        ),
    ],
)
def test_v11_plan_rejects_missing_or_misaligned_context_commitments(
    mutation,
    message,
):
    payload = _v11_plan_payload()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        DomainCaseInputPlanArtifact.model_validate(payload)


def test_v10_plan_rejects_v11_only_context_fields():
    payload = _v11_plan_payload()
    payload["schema_version"] = "1.0"

    with pytest.raises(ValueError, match="schema 1.0"):
        DomainCaseInputPlanArtifact.model_validate(payload)
