import shutil
from pathlib import Path

from scripts.check_project_governance import check_project_governance


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_governance_files_are_consistent():
    assert check_project_governance(PROJECT_ROOT) == []


def test_project_governance_rejects_a_stale_active_plan(tmp_path):
    shutil.copytree(PROJECT_ROOT / ".planning", tmp_path / ".planning")
    shutil.copytree(PROJECT_ROOT / "docs", tmp_path / "docs")
    shutil.copy(PROJECT_ROOT / "AGENTS.md", tmp_path / "AGENTS.md")

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
