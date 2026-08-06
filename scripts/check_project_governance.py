from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_utf8(path: Path, errors: list[str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing required file: {path}")
        return ""
    except UnicodeDecodeError:
        errors.append(f"file is not valid UTF-8: {path}")
        return ""

    if not text.strip():
        errors.append(f"required file is empty: {path}")
    return text


def _front_matter(text: str, path: Path, errors: list[str]) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"missing YAML front matter: {path}")
        return {}

    try:
        closing_index = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        errors.append(f"unterminated YAML front matter: {path}")
        return {}

    try:
        value = yaml.safe_load("\n".join(lines[1:closing_index]))
    except yaml.YAMLError as exc:
        errors.append(f"invalid YAML front matter in {path}: {exc}")
        return {}

    if not isinstance(value, dict):
        errors.append(f"YAML front matter must be an object: {path}")
        return {}
    return value


def _markdown_section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)",
        text,
    )
    return match.group(1).strip() if match else None


def _check_active_plan(root: Path, checkpoint: str, errors: list[str]) -> None:
    planning_root = root / ".planning"
    pointer_path = planning_root / ".active_plan"
    pointer = _read_utf8(pointer_path, errors).strip()
    if not pointer:
        return

    relative_pointer = Path(pointer)
    if (
        relative_pointer.is_absolute()
        or len(relative_pointer.parts) != 1
        or relative_pointer.name in {".", ".."}
    ):
        errors.append(
            ".planning/.active_plan must contain one local plan directory name"
        )
        return

    plan_dir = planning_root / relative_pointer
    task_plan = _read_utf8(plan_dir / "task_plan.md", errors)
    _read_utf8(plan_dir / "progress.md", errors)
    _read_utf8(plan_dir / "findings.md", errors)
    if not task_plan:
        return

    current_phase = _markdown_section(task_plan, "Current Phase")
    next_step = _markdown_section(task_plan, "Next Step")
    if current_phase is None:
        errors.append("active task_plan.md is missing a Current Phase section")
    elif checkpoint not in current_phase:
        errors.append(
            "active plan Current Phase does not contain canonical checkpoint "
            f"{checkpoint!r}"
        )

    if next_step is None:
        errors.append("active task_plan.md is missing a Next Step section")
    elif checkpoint not in next_step:
        errors.append(
            "active plan Next Step does not contain canonical checkpoint "
            f"{checkpoint!r}"
        )

    in_progress_count = len(
        re.findall(r"(?m)^- Status:\s*in_progress\s*$", task_plan)
    )
    if in_progress_count != 1:
        errors.append(
            "active task_plan.md must contain exactly one in_progress phase; "
            f"found {in_progress_count}"
        )


def _check_requirements(root: Path, errors: list[str]) -> None:
    path = root / "docs" / "requirements_change_log.md"
    text = _read_utf8(path, errors)
    if not text:
        return

    requirement_ids = [
        int(value)
        for value in re.findall(r"(?m)^\|\s*RQ-(\d{3})\s*\|", text)
    ]
    if not requirement_ids:
        errors.append("requirements_change_log.md contains no RQ entries")
        return
    if len(requirement_ids) != len(set(requirement_ids)):
        errors.append("requirements_change_log.md contains duplicate RQ IDs")
    if requirement_ids != sorted(requirement_ids):
        errors.append("requirements_change_log.md RQ IDs are not ordered")
    expected_ids = list(range(1, max(requirement_ids) + 1))
    if requirement_ids != expected_ids:
        errors.append("requirements_change_log.md RQ IDs must be append-only and contiguous")


def _check_roadmap(root: Path, main_stage: int, errors: list[str]) -> None:
    path = root / "docs" / "roadmap.md"
    text = _read_utf8(path, errors)
    if not text:
        return

    overview = _markdown_section(text, "九阶段总览")
    if overview is None:
        errors.append("roadmap.md is missing the 九阶段总览 section")
        return

    stage_rows = re.findall(r"(?m)^\|\s*([0-8])\s*\|.*$", overview)
    if [int(value) for value in stage_rows] != list(range(9)):
        errors.append("roadmap.md must list each main stage exactly once from 0 through 8")

    current_row = re.search(
        rf"(?m)^\|\s*{main_stage}\s*\|.*$",
        overview,
    )
    if current_row is not None and "进行中" not in current_row.group(0):
        errors.append(
            f"roadmap.md stage {main_stage} must be marked as 进行中"
        )


def _check_working_agreement(root: Path, errors: list[str]) -> None:
    path = root / "AGENTS.md"
    text = _read_utf8(path, errors)
    if not text:
        return

    required_references = (
        "docs/project_execution_state.md",
        ".planning/.active_plan",
        "docs/requirements_change_log.md",
        "docs/roadmap_change_history.md",
        "scripts/check_project_governance.py",
    )
    for reference in required_references:
        if reference not in text:
            errors.append(f"AGENTS.md does not require {reference}")


def check_project_governance(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    state_path = root / "docs" / "project_execution_state.md"
    state_text = _read_utf8(state_path, errors)
    state = _front_matter(state_text, state_path, errors) if state_text else {}

    required_fields = {
        "state_schema": int,
        "main_stage": int,
        "substage_group": str,
        "current_checkpoint": str,
        "status": str,
    }
    for field, expected_type in required_fields.items():
        value = state.get(field)
        if not isinstance(value, expected_type):
            errors.append(
                f"project execution state field {field!r} must be "
                f"{expected_type.__name__}"
            )

    if state.get("state_schema") not in {None, 1}:
        errors.append("unsupported project execution state schema")

    main_stage = state.get("main_stage")
    if isinstance(main_stage, int) and main_stage not in range(9):
        errors.append("main_stage must be between 0 and 8")

    status = state.get("status")
    if isinstance(status, str) and status not in {
        "pending",
        "in_progress",
        "complete",
        "blocked",
    }:
        errors.append(f"unsupported project status: {status}")

    checkpoint = state.get("current_checkpoint")
    if isinstance(checkpoint, str):
        next_step_matches = re.findall(
            r"(?m)^- 唯一下一步[：:]\s*(.+?)\s*$",
            state_text,
        )
        if len(next_step_matches) != 1:
            errors.append(
                "project_execution_state.md must contain exactly one "
                "唯一下一步 metadata line"
            )
        elif checkpoint not in next_step_matches[0]:
            errors.append(
                "human-readable 唯一下一步 does not match canonical "
                f"checkpoint {checkpoint!r}"
            )
        _check_active_plan(root, checkpoint, errors)

    _check_requirements(root, errors)
    if isinstance(main_stage, int):
        _check_roadmap(root, main_stage, errors)
    _check_working_agreement(root, errors)
    _read_utf8(root / "docs" / "roadmap_change_history.md", errors)

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check RiftCoach planning and stage-governance consistency."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root. Defaults to the repository containing this script.",
    )
    args = parser.parse_args()

    errors = check_project_governance(args.root)
    if errors:
        print("Project governance check failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Project governance check passed.")


if __name__ == "__main__":
    main()
