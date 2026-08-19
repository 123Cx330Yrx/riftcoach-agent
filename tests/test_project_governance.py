import shutil
from pathlib import Path

import yaml

from scripts.check_project_governance import check_project_governance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEARNING_DIMENSIONS = (
    "problem_and_principle",
    "design_and_implementation",
    "code_map",
    "data_and_control_flow",
    "verification",
    "runbook",
    "failure_security_boundary",
    "interview_wording",
)


def _copy_governance_tree(tmp_path: Path) -> None:
    shutil.copytree(PROJECT_ROOT / ".planning", tmp_path / ".planning")
    shutil.copytree(PROJECT_ROOT / "docs", tmp_path / "docs")
    shutil.copy(PROJECT_ROOT / "AGENTS.md", tmp_path / "AGENTS.md")
    coverage_path = tmp_path / "docs" / "learning" / "coverage.yaml"
    if not coverage_path.exists():
        coverage_path.parent.mkdir(parents=True)
        evidence = {
            dimension: ["docs/roadmap.md"] for dimension in LEARNING_DIMENSIONS
        }
        _write_learning_coverage(
            tmp_path,
            {
                "schema": 1,
                "groups": [
                    {
                        "id": "completed-baseline",
                        "sequence": 10,
                        "covers": ["completed-baseline"],
                        "status": "complete",
                        "evidence": evidence,
                    },
                    {
                        "id": "current-checkpoint",
                        "sequence": 20,
                        "covers": ["6B-3-conversation-message-foundation"],
                        "status": "planned",
                        "evidence": {},
                    },
                ],
                "canonical_order": [
                    "completed-baseline",
                    "current-checkpoint",
                ],
            },
        )


def _read_learning_coverage(root: Path) -> dict:
    return yaml.safe_load(
        (root / "docs" / "learning" / "coverage.yaml").read_text(
            encoding="utf-8"
        )
    )


def _write_learning_coverage(root: Path, coverage: dict) -> None:
    (root / "docs" / "learning" / "coverage.yaml").write_text(
        yaml.safe_dump(coverage, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def test_project_governance_files_are_consistent():
    assert check_project_governance(PROJECT_ROOT) == []


def test_project_governance_rejects_a_stale_active_plan(tmp_path):
    _copy_governance_tree(tmp_path)

    active_plan = (tmp_path / ".planning" / ".active_plan").read_text(
        encoding="utf-8"
    ).strip()
    task_plan_path = tmp_path / ".planning" / active_plan / "task_plan.md"
    task_plan = task_plan_path.read_text(encoding="utf-8")
    next_step_start = task_plan.index("## Next Step")
    decisions_start = task_plan.index("## Decisions Made")
    task_plan_path.write_text(
        task_plan[:next_step_start]
        + "## Next Step\n\n直接进入 stale-checkpoint。\n\n"
        + task_plan[decisions_start:],
        encoding="utf-8",
    )

    errors = check_project_governance(tmp_path)

    assert any(
        "Next Step" in error and "canonical checkpoint" in error
        for error in errors
    )


def test_project_governance_requires_learning_coverage_file(tmp_path):
    _copy_governance_tree(tmp_path)
    (tmp_path / "docs" / "learning" / "coverage.yaml").unlink()

    errors = check_project_governance(tmp_path)

    assert any("learning coverage" in error for error in errors)


def test_project_governance_requires_current_checkpoint_coverage(tmp_path):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    for group in coverage["groups"]:
        group["covers"] = [
            value
            for value in group["covers"]
            if value != "6B-3-conversation-message-foundation"
        ]
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any(
        "current checkpoint" in error and "coverage" in error
        for error in errors
    )


def test_project_governance_rejects_complete_coverage_without_all_dimensions(
    tmp_path,
):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    coverage["groups"][0]["evidence"]["interview_wording"] = []
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any(
        "interview_wording" in error and "complete coverage group" in error
        for error in errors
    )


def test_project_governance_rejects_evidence_outside_the_repository(tmp_path):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    coverage["groups"][0]["evidence"]["problem_and_principle"] = [
        "../outside.md"
    ]
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any("outside the repository" in error for error in errors)


def test_project_governance_rejects_missing_or_non_markdown_evidence(tmp_path):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    evidence = coverage["groups"][0]["evidence"]
    evidence["problem_and_principle"] = ["docs/missing-learning-evidence.md"]
    evidence["code_map"] = ["docs/learning/coverage.yaml"]
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any("evidence file does not exist" in error for error in errors)
    assert any("evidence path must reference Markdown" in error for error in errors)


def test_project_governance_rejects_incomplete_group_before_current_checkpoint(
    tmp_path,
):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    current_group_index = next(
        index
        for index, group in enumerate(coverage["groups"])
        if "6B-3-conversation-message-foundation" in group["covers"]
    )
    coverage["groups"][current_group_index - 1]["status"] = "planned"
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any("precedes current checkpoint" in error for error in errors)


def test_project_governance_rejects_reordered_learning_coverage(tmp_path):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    coverage["groups"][0], coverage["groups"][1] = (
        coverage["groups"][1],
        coverage["groups"][0],
    )
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any("sequence must be strictly increasing" in error for error in errors)


def test_project_governance_rejects_reordered_and_renumbered_learning_coverage(
    tmp_path,
):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    coverage["groups"][0], coverage["groups"][1] = (
        coverage["groups"][1],
        coverage["groups"][0],
    )
    # A sequence-only guard cannot detect this mutation; the canonical ID
    # order must remain the authority.
    coverage["groups"][0]["sequence"] = 10
    coverage["groups"][1]["sequence"] = 20
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any("canonical order" in error for error in errors)


def test_project_governance_rejects_a_stale_declared_canonical_order(tmp_path):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    coverage["canonical_order"] = list(reversed(coverage["canonical_order"]))
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any("canonical_order" in error for error in errors)


def test_project_governance_requires_learning_coverage_sequence(tmp_path):
    _copy_governance_tree(tmp_path)
    coverage = _read_learning_coverage(tmp_path)
    coverage["groups"][0].pop("sequence")
    _write_learning_coverage(tmp_path, coverage)

    errors = check_project_governance(tmp_path)

    assert any(
        "must have a non-negative integer sequence" in error
        for error in errors
    )
