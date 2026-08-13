from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.domain_e2e import load_domain_dataset
from app.evaluation.prompt_context_identity import (
    PromptContextSnapshot,
    build_prompt_context_snapshot,
    load_prompt_context_snapshot,
    prepare_domain_experiment,
)


FIXTURES = Path("examples/fixtures")
DATASET_PATH = Path("data/evaluation/domain_e2e_v1_development_cases.json")
SNAPSHOT_PATH = Path(
    "data/evaluation/contracts/recent_form_prompt_context_v1.json"
)
ADMISSION_PATH = Path(
    "data/evaluation/results/domain_e2e_v1_experiment_admission.json"
)


def _summary() -> dict:
    return json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )


def _report() -> str:
    return (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )


def _build(*, skills_root: Path = Path("skills"), summary: dict | None = None):
    return build_prompt_context_snapshot(
        skills_root=skills_root,
        player_summary=summary or _summary(),
        deterministic_report=_report(),
    )


def test_current_prompt_context_snapshot_is_reproducible_and_frozen() -> None:
    first = _build()
    second = _build()
    frozen = load_prompt_context_snapshot(SNAPSHOT_PATH)

    assert first == second == frozen
    assert first.model_dump_json(indent=2) + "\n" == SNAPSHOT_PATH.read_text(
        encoding="utf-8"
    )
    assert first.skill_name == "recent-form-review"
    assert first.skill_version == "0.2.0"
    assert first.context_contract == "context-builder-v1"
    assert first.evaluation_contract == "coach_evaluation@1.0.0"
    assert {row.component_id for row in first.components} >= {
        "knowledge_tool_contract",
        "evaluation_fact_pack_probe",
    }
    assert len(first.snapshot_sha256) == 64
    assert first.case_contexts[0].selected_section_ids
    assert len(first.case_contexts[0].message_fingerprints) == 2


def test_skill_instruction_change_alters_component_and_snapshot_identity(
    tmp_path: Path,
) -> None:
    copied_skills = tmp_path / "skills"
    shutil.copytree("skills", copied_skills)
    instructions = copied_skills / "recent-form-review" / "SKILL.md"
    instructions.write_text(
        instructions.read_text(encoding="utf-8")
        + "\n- Experimental instruction drift.\n",
        encoding="utf-8",
    )

    baseline = _build()
    changed = _build(skills_root=copied_skills)
    before = {row.component_id: row.sha256 for row in baseline.components}
    after = {row.component_id: row.sha256 for row in changed.components}

    assert before["skill_instructions"] != after["skill_instructions"]
    assert before["skill_manifest"] == after["skill_manifest"]
    assert baseline.snapshot_sha256 != changed.snapshot_sha256


def test_fixture_change_alters_case_identity_but_not_component_contracts() -> None:
    summary = _summary()
    summary["recent_summary"]["wins"] += 1

    baseline = _build()
    changed = _build(summary=summary)

    assert baseline.components == changed.components
    assert baseline.case_contexts != changed.case_contexts
    assert baseline.snapshot_sha256 != changed.snapshot_sha256


def test_snapshot_self_digest_and_schema_fail_closed() -> None:
    payload = load_prompt_context_snapshot(SNAPSHOT_PATH).model_dump(mode="json")
    payload["snapshot_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="snapshot_sha256"):
        PromptContextSnapshot.model_validate(payload)

    payload = load_prompt_context_snapshot(SNAPSHOT_PATH).model_dump(mode="json")
    payload["raw_prompt"] = "must never enter the public snapshot"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PromptContextSnapshot.model_validate(payload)


def test_public_snapshot_contains_no_probe_or_prompt_bodies() -> None:
    serialized = SNAPSHOT_PATH.read_text(encoding="utf-8")

    for protected_text in (
        "FACT_SENTINEL",
        "PLAYER_SENTINEL",
        "REPORT_SENTINEL",
        "INVALID_OUTPUT_SENTINEL",
        "EVIDENCE_SENTINEL",
        "CORRECTION_SENTINEL",
        "你是独立事实审查员",
        "你是报告校订员",
        "分析我最近几局的状态",
    ):
        assert protected_text not in serialized


def test_dataset_contract_binds_frozen_prompt_context_snapshot() -> None:
    dataset = load_domain_dataset(DATASET_PATH)
    snapshot = load_prompt_context_snapshot(SNAPSHOT_PATH)

    assert dataset.schema_version == "1.1"
    assert dataset.dataset_version == "1.1.0"
    assert dataset.contract_snapshot.prompt_context_snapshot_id == (
        snapshot.snapshot_id
    )
    assert dataset.contract_snapshot.prompt_context_snapshot_sha256 == (
        snapshot.snapshot_sha256
    )


def test_offline_admission_rebuilds_current_identity_and_rejects_drift(
    tmp_path: Path,
) -> None:
    admission = prepare_domain_experiment(
        project_root=Path.cwd(),
        dataset_path=DATASET_PATH,
        snapshot_path=SNAPSHOT_PATH,
    )
    frozen = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))

    assert admission.model_dump(mode="json") == frozen
    assert admission.admitted is True
    assert admission.external_provider_calls == 0

    copied_skills = tmp_path / "skills"
    shutil.copytree("skills", copied_skills)
    instructions = copied_skills / "recent-form-review" / "SKILL.md"
    instructions.write_text(
        instructions.read_text(encoding="utf-8") + "\nDrift.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Prompt/Context snapshot mismatch"):
        prepare_domain_experiment(
            project_root=Path.cwd(),
            dataset_path=DATASET_PATH,
            snapshot_path=SNAPSHOT_PATH,
            skills_root=copied_skills,
        )


def test_prepare_cli_is_reproducible_and_never_calls_provider(
    tmp_path: Path,
) -> None:
    output = tmp_path / "admission.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_domain_e2e_experiment.py",
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        ADMISSION_PATH.read_text(encoding="utf-8")
    )
    assert "External Provider calls: 0" in completed.stdout


def test_prepare_cli_rejects_paths_outside_project_before_output(
    tmp_path: Path,
) -> None:
    outside_dataset = tmp_path / "outside.json"
    outside_dataset.write_text("{}", encoding="utf-8")
    output = tmp_path / "must-not-exist.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_domain_e2e_experiment.py",
            "--dataset",
            str(outside_dataset),
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert "inside the project root" in completed.stderr
    assert not output.exists()
