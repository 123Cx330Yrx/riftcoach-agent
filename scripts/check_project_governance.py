from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEARNING_COVERAGE_DIMENSIONS = (
    "problem_and_principle",
    "design_and_implementation",
    "code_map",
    "data_and_control_flow",
    "verification",
    "runbook",
    "failure_security_boundary",
    "interview_wording",
)

# The coverage ledger is an execution gate, not an unordered catalog.  Keep
# the canonical order here so a future edit cannot reorder groups (and simply
# renumber ``sequence``) to make an incomplete predecessor look complete.
# When a new checkpoint is intentionally added, update this tuple and the
# ledger in the same reviewed change.
LEARNING_COVERAGE_CANONICAL_ORDER = (
    "stage-0-baseline-and-reference-evidence",
    "stage-1-domain-core-v1",
    "stage-2-harness-v1",
    "stage-3-provider-tool-runtime",
    "stage-4-rag-v1",
    "stage-5a-minimal-agent-loop",
    "stage-5b-skill-contract-v1",
    "stage-5c-skill-router-v1",
    "stage-5d-constrained-agent-loop",
    "stage-5e-agent-runtime-v1",
    "stage-5p-product-slice",
    "stage-5f-pi-adoption-experiment",
    "stage-6a-postgresql-task-product",
    "stage-6-session-memory-entry-design",
    "6b-1-player-identity-link-foundation",
    "6b-2-async-player-link-worker-api",
    "6b-3-conversation-message-foundation",
    "6b-4-conversation-bound-recent-review-identity",
    "6b-5-memory-candidate-write-gate",
    "6b-6-preferences-profile-review-memory",
    "6b-7-training-plan-progress",
    "6b-8-memory-aware-context-typed-turns",
    "6b-9-lifecycle-export-exit-review",
    "stage-7-standard-mcp-dynamic-meta-entry-design",
    "7-1-mcp-client-contract",
    "7-2-mcp-transport-and-discovery",
    "7-3-opgg-meta-adapter",
    "7-4-riftcoach-mcp-server",
    "7-5-mcp-interoperability-exit-review",
)


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
        "docs/learning/README.md",
        "docs/learning/coverage.yaml",
        "scripts/check_project_governance.py",
    )
    for reference in required_references:
        if reference not in text:
            errors.append(f"AGENTS.md does not require {reference}")


def _check_learning_evidence_path(
    root: Path,
    group_id: str,
    dimension: str,
    value: object,
    checked_paths: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(
            f"learning coverage group {group_id!r} dimension {dimension!r} "
            "contains a non-string or empty evidence path"
        )
        return

    if value in checked_paths:
        return
    checked_paths.add(value)

    relative_path = Path(value)
    if relative_path.is_absolute():
        errors.append(
            f"learning evidence path is outside the repository: {value!r}"
        )
        return

    evidence_path = (root / relative_path).resolve()
    try:
        evidence_path.relative_to(root)
    except ValueError:
        errors.append(
            f"learning evidence path is outside the repository: {value!r}"
        )
        return

    if evidence_path.suffix.lower() != ".md":
        errors.append(
            f"learning evidence path must reference Markdown: {value!r}"
        )
        return
    if not evidence_path.is_file():
        errors.append(f"learning evidence file does not exist: {value!r}")
        return
    _read_utf8(evidence_path, errors)


def _check_learning_coverage(
    root: Path,
    checkpoint: str | None,
    errors: list[str],
) -> None:
    path = root / "docs" / "learning" / "coverage.yaml"
    if not path.is_file():
        errors.append(f"missing learning coverage file: {path}")
        return

    text = _read_utf8(path, errors)
    if not text:
        return
    try:
        coverage = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"invalid learning coverage YAML in {path}: {exc}")
        return

    if not isinstance(coverage, dict):
        errors.append("learning coverage must be a YAML object")
        return
    if coverage.get("schema") != 1:
        errors.append("unsupported learning coverage schema")

    groups = coverage.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append("learning coverage must contain a non-empty groups list")
        return

    declared_order = coverage.get("canonical_order")
    if declared_order != list(LEARNING_COVERAGE_CANONICAL_ORDER):
        errors.append(
            "learning coverage canonical_order must match the governance contract"
        )

    group_ids: set[str] = set()
    cover_owners: dict[str, str] = {}
    current_group_indexes: list[int] = []
    statuses: list[str | None] = []
    sequences: list[int | None] = []
    checked_evidence_paths: set[str] = set()

    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"learning coverage group at index {index} must be an object")
            statuses.append(None)
            sequences.append(None)
            continue

        group_id = group.get("id")
        if not isinstance(group_id, str) or not group_id.strip():
            errors.append(f"learning coverage group at index {index} has no valid id")
            group_id = f"index-{index}"
        elif group_id in group_ids:
            errors.append(f"duplicate learning coverage group id: {group_id!r}")
        group_ids.add(group_id)

        sequence = group.get("sequence")
        if type(sequence) is not int or sequence < 0:
            errors.append(
                f"learning coverage group {group_id!r} must have a non-negative "
                "integer sequence"
            )
            sequences.append(None)
        else:
            sequences.append(sequence)

        status = group.get("status")
        if status not in {"complete", "planned"}:
            errors.append(
                f"learning coverage group {group_id!r} has unsupported status: "
                f"{status!r}"
            )
            statuses.append(None)
        else:
            statuses.append(status)

        covers = group.get("covers")
        if not isinstance(covers, list) or not covers:
            errors.append(
                f"learning coverage group {group_id!r} must cover at least one checkpoint"
            )
            covers = []
        for covered_checkpoint in covers:
            if not isinstance(covered_checkpoint, str) or not covered_checkpoint.strip():
                errors.append(
                    f"learning coverage group {group_id!r} contains an invalid checkpoint"
                )
                continue
            previous_owner = cover_owners.get(covered_checkpoint)
            if previous_owner is not None:
                errors.append(
                    f"learning checkpoint {covered_checkpoint!r} is covered by both "
                    f"{previous_owner!r} and {group_id!r}"
                )
            else:
                cover_owners[covered_checkpoint] = group_id
            if checkpoint is not None and covered_checkpoint == checkpoint:
                current_group_indexes.append(index)

        evidence = group.get("evidence", {})
        if not isinstance(evidence, dict):
            errors.append(
                f"learning coverage group {group_id!r} evidence must be an object"
            )
            evidence = {}

        for dimension in LEARNING_COVERAGE_DIMENSIONS:
            paths = evidence.get(dimension)
            if status == "complete" and (not isinstance(paths, list) or not paths):
                errors.append(
                    f"complete coverage group {group_id!r} must provide "
                    f"dimension {dimension!r}"
                )
                continue
            if paths is None:
                continue
            if not isinstance(paths, list):
                errors.append(
                    f"learning coverage group {group_id!r} dimension "
                    f"{dimension!r} must be a list"
                )
                continue
            for evidence_value in paths:
                _check_learning_evidence_path(
                    root,
                    group_id,
                    dimension,
                    evidence_value,
                    checked_evidence_paths,
                    errors,
                )

        unknown_dimensions = set(evidence) - set(LEARNING_COVERAGE_DIMENSIONS)
        for dimension in sorted(unknown_dimensions):
            errors.append(
                f"learning coverage group {group_id!r} has unknown evidence "
                f"dimension {dimension!r}"
            )

    valid_sequences = [value for value in sequences if value is not None]
    if len(valid_sequences) != len(set(valid_sequences)):
        errors.append("learning coverage sequence values must be unique")
    if len(valid_sequences) == len(sequences) and any(
        current >= following
        for current, following in zip(valid_sequences, valid_sequences[1:])
    ):
        errors.append("learning coverage sequence must be strictly increasing")

    actual_order = [
        group.get("id")
        for group in groups
        if isinstance(group, dict) and isinstance(group.get("id"), str)
    ]
    if actual_order != list(LEARNING_COVERAGE_CANONICAL_ORDER):
        errors.append(
            "learning coverage groups must follow the canonical order; "
            "update the governance constant and ledger together for an intentional change"
        )

    if checkpoint is None:
        return
    if not current_group_indexes:
        errors.append(
            f"current checkpoint {checkpoint!r} is missing from learning coverage"
        )
        return
    if len(current_group_indexes) > 1:
        errors.append(
            f"current checkpoint {checkpoint!r} appears in multiple coverage groups"
        )
        return

    current_index = current_group_indexes[0]
    for index, status in enumerate(statuses[:current_index]):
        if status != "complete":
            group = groups[index]
            group_id = (
                group.get("id", f"index-{index}")
                if isinstance(group, dict)
                else f"index-{index}"
            )
            errors.append(
                f"learning coverage group {group_id!r} precedes current checkpoint "
                f"{checkpoint!r} but is not complete"
            )


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

    _check_learning_coverage(
        root,
        checkpoint if isinstance(checkpoint, str) else None,
        errors,
    )

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
