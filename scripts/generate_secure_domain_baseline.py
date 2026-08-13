"""Generate the versioned offline D2 development identity and dataset."""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.domain_e2e import DomainEvaluationDataset
from app.evaluation.prompt_context_identity import build_prompt_context_snapshot


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/evaluation/contracts/recent_form_prompt_context_v1_1.json"
DATASET = ROOT / "data/evaluation/domain_e2e_v1_1_secure_executable_development_cases.json"


def main() -> None:
    summary = json.loads(
        (ROOT / "examples/fixtures/player_summary_demo.json").read_text(
            encoding="utf-8"
        )
    )
    report = (ROOT / "examples/fixtures/deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )
    snapshot = build_prompt_context_snapshot(
        skills_root=ROOT / "skills",
        player_summary=summary,
        deterministic_report=report,
        snapshot_id="recent-form-prompt-context-v1-1",
        evaluation_contract_version="1.1.0",
    )
    SNAPSHOT.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")

    old = json.loads(
        (ROOT / "data/evaluation/domain_e2e_v1_executable_development_cases.json")
        .read_text(encoding="utf-8")
    )
    old["dataset_id"] = "domain-e2e-v1-1-secure-executable-development"
    old["dataset_version"] = "1.1.0"
    old["contract_snapshot"] = {
        "skill_name": snapshot.skill_name,
        "skill_version": snapshot.skill_version,
        "context_contract": snapshot.context_contract,
        "evaluation_contract": snapshot.evaluation_contract,
        "prompt_context_snapshot_id": snapshot.snapshot_id,
        "prompt_context_snapshot_sha256": snapshot.snapshot_sha256,
    }
    old["contamination_notes"] = [
        "All cases are public synthetic development controls for the versioned security-aware evaluator.",
        "The fixed demo summary, scripted responses, fact oracle, citation oracle, and injection canaries are known to the implementation.",
        "This dataset must not be reported as held-out evidence or real Provider quality.",
    ]
    old["lifecycle_policy"] = (
        "Development-only executable controls for coach_evaluation@1.1.0. "
        "Prompt/Context admission is mandatory before case execution. "
        "Known injection cases must be blocked by Harness and never promoted to held-out."
    )
    dataset = DomainEvaluationDataset.model_validate(old)
    DATASET.write_text(dataset.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"snapshot={SNAPSHOT}")
    print(f"dataset={DATASET}")
    print(f"snapshot_sha256={snapshot.snapshot_sha256}")


if __name__ == "__main__":
    main()
