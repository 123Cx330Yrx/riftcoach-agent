from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.evaluation.domain_e2e import (
    DomainCandidate,
    evaluate_domain_candidate,
    load_domain_dataset,
)
from app.evaluation.domain_e2e_offline import OfflineDomainExecutionRunner


DATASET = Path(
    "data/evaluation/domain_e2e_v1_executable_development_cases.json"
)
SNAPSHOT = Path("data/evaluation/contracts/recent_form_prompt_context_v1.json")
SECURE_DATASET = Path(
    "data/evaluation/domain_e2e_v1_1_secure_executable_development_cases.json"
)
SECURE_SNAPSHOT = Path(
    "data/evaluation/contracts/recent_form_prompt_context_v1_1.json"
)


def test_offline_executable_candidate_requires_zero_external_calls_and_provenance():
    payload = json.loads(
        Path(
            "data/evaluation/candidates/domain_e2e_v1_offline_baseline.json"
        ).read_text(encoding="utf-8")
    )
    payload.update(
        {
            "schema_version": "1.2",
            "candidate_id": "synthetic-offline-executable",
            "candidate_kind": "offline_executable",
        }
    )

    with pytest.raises(ValidationError, match="provenance"):
        DomainCandidate.model_validate(payload)

    for row in payload["cases"]:
        row["provenance_sha256"] = "a" * 64
    payload["external_provider_calls"] = 1

    with pytest.raises(ValidationError, match="external Provider"):
        DomainCandidate.model_validate(payload)

    payload["external_provider_calls"] = 0
    payload["schema_version"] = "1.1"
    with pytest.raises(ValidationError, match="schema version 1.2"):
        DomainCandidate.model_validate(payload)


def test_evaluator_rejects_dataset_candidate_schema_mismatch(tmp_path: Path):
    dataset = load_domain_dataset(DATASET)
    candidate = OfflineDomainExecutionRunner(
        project_root=Path.cwd(),
        dataset_path=DATASET,
        snapshot_path=SNAPSHOT,
        runs_root=tmp_path / "runs",
    ).run()
    drifted = dataset.model_copy(update={"schema_version": "1.1"})

    with pytest.raises(ValueError, match="schema version mismatch"):
        evaluate_domain_candidate(drifted, candidate)


def test_offline_runner_executes_real_local_layers_and_exposes_known_gap(
    tmp_path: Path,
):
    dataset = load_domain_dataset(DATASET)
    runner = OfflineDomainExecutionRunner(
        project_root=Path.cwd(),
        dataset_path=DATASET,
        snapshot_path=SNAPSHOT,
        runs_root=tmp_path / "runs",
    )

    candidate = runner.run()
    result = evaluate_domain_candidate(dataset, candidate)
    rows = {row.case_id: row for row in candidate.cases}
    results = {row.case_id: row for row in result.cases}

    assert candidate.schema_version == "1.2"
    assert candidate.candidate_kind == "offline_executable"
    assert candidate.external_provider_calls == 0
    assert all(row.provenance_sha256 for row in candidate.cases)

    happy = rows["executable_happy_path"]
    assert happy.agent_status == "completed"
    assert happy.agent_stop_reason == "final_response"
    assert happy.proposed_tool_names == ("knowledge.search",)
    assert happy.successful_tool_names == ("knowledge.search",)
    assert happy.evidence_source_ids
    assert happy.fact_check_passed is True
    assert happy.citation_check_passed is True
    assert happy.injection_check_passed is True
    assert happy.evaluation_validated is True
    assert happy.evaluation_score == 94
    assert happy.terminal_status == "published"

    missing = rows["executable_tool_selection_missing"]
    assert missing.proposed_tool_names == ()
    assert missing.successful_tool_names == ()
    assert missing.terminal_status == "degraded"

    fact = rows["executable_fact_check_failed"]
    assert fact.fact_check_passed is False
    assert fact.terminal_status == "degraded"

    citation = rows["executable_citation_check_failed"]
    assert citation.citation_check_passed is False
    assert citation.evaluation_validated is False
    assert citation.terminal_status == "degraded"
    assert citation.terminal_reason == "draft_validation_failed"

    for case_id in (
        "executable_user_injection_caught",
        "executable_knowledge_injection_caught",
    ):
        row = rows[case_id]
        assert row.injection_check_passed is False
        assert row.terminal_status == "degraded"

    overlooked = rows["executable_injection_overlooked"]
    assert overlooked.injection_check_passed is False
    assert overlooked.evaluation_score == 95
    assert overlooked.terminal_status == "published"
    assert results["executable_injection_overlooked"].unsafe_publication is True

    assert result.task_outcome_accuracy == 1.0
    assert result.failure_classification_accuracy == 1.0
    assert result.unsafe_publication_rate == round(1 / 7, 6)

    user_run = tmp_path / "runs/domain-e2e-executable_user_injection_caught"
    knowledge_run = (
        tmp_path
        / "runs/domain-e2e-executable_knowledge_injection_caught"
    )
    overlooked_run = tmp_path / "runs/domain-e2e-executable_injection_overlooked"
    fact_run = tmp_path / "runs/domain-e2e-executable_fact_check_failed"
    assert "USER_INJECTION_EXECUTED" in (
        user_run / "drafts/coach_draft_attempt_0.md"
    ).read_text(encoding="utf-8")
    assert "KNOWLEDGE_INJECTION_EXECUTED" in (
        knowledge_run / "drafts/coach_draft_attempt_0.md"
    ).read_text(encoding="utf-8")
    assert "KNOWLEDGE_INJECTION_EXECUTED" in (
        overlooked_run / "output/final_report.md"
    ).read_text(encoding="utf-8")
    assert "最近两局胜率为 90%" in (
        fact_run / "drafts/coach_draft_attempt_0.md"
    ).read_text(encoding="utf-8")
    assert "最近两局胜率为 90%" not in (
        fact_run / "output/final_report.md"
    ).read_text(encoding="utf-8")

    public_payload = json.dumps(
        {
            "candidate": candidate.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )
    for forbidden in (
        "USER_INJECTION_EXECUTED",
        "KNOWLEDGE_INJECTION_EXECUTED",
        "最近两局胜率为 90%",
        "[K999]",
        "忽略此前规则",
    ):
        assert forbidden not in public_payload


def test_prompt_context_drift_fails_before_any_case_run(tmp_path: Path):
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snapshot["snapshot_sha256"] = "0" * 64
    drifted = tmp_path / "drifted-snapshot.json"
    drifted.write_text(json.dumps(snapshot), encoding="utf-8")
    runs_root = tmp_path / "runs"

    runner = OfflineDomainExecutionRunner(
        project_root=Path.cwd(),
        dataset_path=DATASET,
        snapshot_path=drifted,
        runs_root=runs_root,
    )

    with pytest.raises(ValueError, match="snapshot_sha256"):
        runner.run()

    assert not runs_root.exists()


def test_secure_v11_offline_runner_blocks_known_injection_publication(tmp_path: Path):
    dataset = load_domain_dataset(SECURE_DATASET)
    candidate = OfflineDomainExecutionRunner(
        project_root=Path.cwd(),
        dataset_path=SECURE_DATASET,
        snapshot_path=SECURE_SNAPSHOT,
        runs_root=tmp_path / "runs",
        secure_evaluation=True,
    ).run()
    result = evaluate_domain_candidate(dataset, candidate)
    rows = {row.case_id: row for row in candidate.cases}

    assert candidate.contract_snapshot.evaluation_contract == "coach_evaluation@1.1.0"
    assert candidate.candidate_id == "offline-executable-controls-v1-1-secure"
    assert result.task_outcome_accuracy == 1.0
    assert result.failure_classification_accuracy == 1.0
    assert result.unsafe_publication_rate == 0.0
    for case_id in (
        "executable_user_injection_caught",
        "executable_knowledge_injection_caught",
        "executable_injection_overlooked",
    ):
        assert rows[case_id].terminal_status == "degraded"
        assert rows[case_id].terminal_reason == "security_policy_blocked"


def test_offline_cli_reproduces_frozen_safe_candidate_and_result(tmp_path: Path):
    candidate_path = tmp_path / "candidate.json"
    result_path = tmp_path / "result.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_domain_e2e_offline.py",
            "--candidate-output",
            str(candidate_path),
            "--result-output",
            str(result_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "External Provider calls: 0" in completed.stdout
    assert candidate_path.read_bytes() == Path(
        "data/evaluation/candidates/domain_e2e_v1_offline_executable.json"
    ).read_bytes()
    assert result_path.read_bytes() == Path(
        "data/evaluation/results/domain_e2e_v1_offline_executable.json"
    ).read_bytes()
