"""Run the no-network Stage 8 experiment under a clean exact-SHA lifecycle."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.stage8_experiment import (  # noqa: E402
    ExperimentRecord,
    ExperimentSplit,
    ImmutableExperimentOutput,
    load_experiment_record,
    prepare_holdout_admission,
    run_stage8_experiment,
    write_experiment_record_exclusive,
)
from scripts.prepare_second_provider_experiment import read_clean_code_sha  # noqa: E402


_DEFAULT_DEVELOPMENT = Path("tmp/stage8/multi_agent_development_v1.json")
_DEFAULT_HOLDOUT = Path(
    "data/evaluation/results/stage8/role_isolated_multi_agent_holdout_v1.json"
)
_DEFAULT_RUNS = Path("data/runs/evaluation/stage8_multi_agent")


@dataclass(frozen=True)
class Stage8ExperimentCliOptions:
    split: ExperimentSplit
    public_ci_sha: str
    confirm_public_ci_success: bool
    confirm_holdout: bool = False
    development_result: Path = _DEFAULT_DEVELOPMENT
    output: Path | None = None
    runs_root: Path = _DEFAULT_RUNS


CodeShaReader = Callable[[Path], str]
ExperimentRunner = Callable[..., ExperimentRecord]


def run_cli(
    options: Stage8ExperimentCliOptions,
    *,
    repository_root: Path = PROJECT_ROOT,
    code_sha_reader: CodeShaReader = read_clean_code_sha,
    experiment_runner: ExperimentRunner = run_stage8_experiment,
) -> ExperimentRecord:
    root = repository_root.resolve()
    code_sha = code_sha_reader(root)
    if code_sha != options.public_ci_sha:
        raise RuntimeError("public CI SHA must equal the clean repository HEAD")
    if not options.confirm_public_ci_success:
        raise RuntimeError("exact-SHA public CI success must be confirmed")

    development_path = _inside_allowed_root(
        root,
        options.development_result,
        allowed_root=root / "tmp" / "stage8",
        label="development result",
    )
    runs_root = _inside_allowed_root(
        root,
        options.runs_root,
        allowed_root=root / "data" / "runs" / "evaluation" / "stage8_multi_agent",
        label="runs root",
        allow_root_itself=True,
    )
    if options.split is ExperimentSplit.DEVELOPMENT:
        output = (
            _inside_allowed_root(
                root,
                options.output,
                allowed_root=root / "tmp" / "stage8",
                label="development output",
            )
            if options.output is not None
            else development_path
        )
        if output.exists():
            raise FileExistsError(
                "development evidence is immutable and cannot be overwritten"
            )
        record = experiment_runner(
            repository_root=root,
            split=ExperimentSplit.DEVELOPMENT,
            code_sha=code_sha,
            runs_root=runs_root,
        )
        write_experiment_record_exclusive(output, record)
        return load_experiment_record(output)

    if not options.confirm_holdout:
        raise RuntimeError("the calibration-excluded holdout requires confirmation")
    output_value = options.output or _DEFAULT_HOLDOUT
    output = _inside_allowed_root(
        root,
        output_value,
        allowed_root=root / "data" / "evaluation" / "results" / "stage8",
        label="holdout output",
    )
    admission = prepare_holdout_admission(
        repository_root=root,
        development_result_path=development_path,
        code_sha=code_sha,
        public_ci_sha=options.public_ci_sha,
        confirm_public_ci_success=options.confirm_public_ci_success,
        confirm_holdout=options.confirm_holdout,
    )
    reservation = ImmutableExperimentOutput.reserve(
        output,
        experiment_id=admission.holdout_experiment_id,
    )
    try:
        record = experiment_runner(
            repository_root=root,
            split=ExperimentSplit.HOLDOUT,
            code_sha=code_sha,
            public_ci_sha=options.public_ci_sha,
            admission=admission,
            runs_root=runs_root,
        )
        reservation.commit(record)
        return load_experiment_record(output)
    except Exception:
        reservation.abandon()
        raise


def _inside_allowed_root(
    repository_root: Path,
    value: Path,
    *,
    allowed_root: Path,
    label: str,
    allow_root_itself: bool = False,
) -> Path:
    candidate = value if value.is_absolute() else repository_root / value
    resolved = candidate.resolve()
    boundary = allowed_root.resolve()
    if not resolved.is_relative_to(boundary):
        raise ValueError(f"{label} must remain inside {boundary.relative_to(repository_root)}")
    if not allow_root_itself and resolved == boundary:
        raise ValueError(f"{label} must name a file below its allowed directory")
    if not allow_root_itself and resolved.suffix.lower() != ".json":
        raise ValueError(f"{label} must be a JSON file")
    return resolved


def _parse_args(argv: Sequence[str] | None = None) -> Stage8ExperimentCliOptions:
    parser = argparse.ArgumentParser(
        description="Run the bounded, no-network Stage 8 three-path experiment."
    )
    parser.add_argument(
        "--split",
        choices=tuple(item.value for item in ExperimentSplit),
        required=True,
    )
    parser.add_argument("--public-ci-sha", required=True)
    parser.add_argument("--confirm-public-ci-success", action="store_true")
    parser.add_argument("--confirm-holdout", action="store_true")
    parser.add_argument("--development-result", type=Path, default=_DEFAULT_DEVELOPMENT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs-root", type=Path, default=_DEFAULT_RUNS)
    values = parser.parse_args(argv)
    return Stage8ExperimentCliOptions(
        split=ExperimentSplit(values.split),
        public_ci_sha=values.public_ci_sha,
        confirm_public_ci_success=values.confirm_public_ci_success,
        confirm_holdout=values.confirm_holdout,
        development_result=values.development_result,
        output=values.output,
        runs_root=values.runs_root,
    )


if __name__ == "__main__":
    result = run_cli(_parse_args())
    print(
        f"split={result.split.value} verdict={result.verdict} "
        f"external_io_calls={result.external_io_calls} "
        f"holdout_executions={result.holdout_executions}"
    )
