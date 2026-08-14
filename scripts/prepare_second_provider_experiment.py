"""Prepare the D5 second-Provider experiment without network or API keys."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.provider_adoption import (
    ExperimentPreparationReport,
    ProviderExperimentPreparationError,
    prepare_second_provider_experiment,
)


_DEFAULT_DATASET = Path(
    "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
)
_DEFAULT_SNAPSHOT = Path(
    "data/evaluation/contracts/recent_form_prompt_context_v1_1.json"
)


@dataclass(frozen=True)
class NoIoExperimentOptions:
    public_ci_sha: str
    confirm_public_ci_success: bool
    dataset: Path = _DEFAULT_DATASET
    snapshot: Path = _DEFAULT_SNAPSHOT
    provider_id: str = "deepseek"
    model: str = "deepseek-v4-pro"
    base_url: str = "https://api.deepseek.com"
    sdk_max_retries: int = 0


def run_cli(
    options: NoIoExperimentOptions,
    *,
    repository_root: Path = PROJECT_ROOT,
    code_sha_reader: Callable[[Path], str] | None = None,
) -> ExperimentPreparationReport:
    """Run only local identity and budget checks; never create a Provider."""

    root = repository_root.resolve()
    dataset = _inside_project(root, options.dataset, label="dataset")
    snapshot = _inside_project(root, options.snapshot, label="snapshot")
    code_sha = (code_sha_reader or _read_clean_code_sha)(root)
    return prepare_second_provider_experiment(
        project_root=root,
        dataset_path=dataset,
        snapshot_path=snapshot,
        code_sha=code_sha,
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
        provider_id=options.provider_id,
        model=options.model,
        base_url=options.base_url,
        sdk_max_retries=options.sdk_max_retries,
    )


def _inside_project(root: Path, value: Path, *, label: str) -> Path:
    path = value if value.is_absolute() else root / value
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must remain inside the project root")
    return resolved


def _read_clean_code_sha(repository_root: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if status.stdout.strip():
        raise RuntimeError("no-I/O preflight requires a clean committed worktree")
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout.strip()


def _parse_args(argv: Sequence[str] | None = None) -> NoIoExperimentOptions:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the frozen D5 experiment without reading a Key, creating "
            "a Provider, calling a model, or running held-out cases."
        )
    )
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument("--snapshot", type=Path, default=_DEFAULT_SNAPSHOT)
    parser.add_argument("--provider-id", default="deepseek")
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--sdk-max-retries", type=int, default=0)
    values = parser.parse_args(argv)
    return NoIoExperimentOptions(
        public_ci_sha=values.public_ci_sha,
        confirm_public_ci_success=values.confirm_public_ci_success,
        dataset=values.dataset,
        snapshot=values.snapshot,
        provider_id=values.provider_id,
        model=values.model,
        base_url=values.base_url,
        sdk_max_retries=values.sdk_max_retries,
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        report = run_cli(_parse_args(argv))
    except (ProviderExperimentPreparationError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"provider={report.provider_id} model={report.requested_model} "
        f"code_sha={report.code_sha} local_preflight_passed=true"
    )
    print(
        f"external_provider_calls={report.external_provider_calls} "
        f"held_out_executed={str(report.held_out_executed).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
