from __future__ import annotations

from pathlib import Path

import pytest

from app.evaluation.stage8_experiment import ExperimentSplit, run_stage8_experiment
from scripts.run_stage8_multi_agent_experiment import (
    Stage8ExperimentCliOptions,
    run_cli,
)


ROOT = Path(__file__).resolve().parents[1]
CODE_SHA = "6" * 40


def _development_record(tmp_path: Path):
    return run_stage8_experiment(
        repository_root=ROOT,
        split=ExperimentSplit.DEVELOPMENT,
        code_sha=CODE_SHA,
        runs_root=tmp_path / "source-runs",
    )


def test_development_cli_requires_clean_exact_public_ci_sha(tmp_path: Path) -> None:
    options = Stage8ExperimentCliOptions(
        split=ExperimentSplit.DEVELOPMENT,
        public_ci_sha="7" * 40,
        confirm_public_ci_success=True,
    )

    with pytest.raises(RuntimeError, match="public CI SHA"):
        run_cli(
            options,
            repository_root=tmp_path,
            code_sha_reader=lambda root: CODE_SHA,
        )


def test_development_cli_writes_one_body_free_result_under_tmp(tmp_path: Path) -> None:
    source = _development_record(tmp_path)
    calls = 0

    def scripted_runner(**kwargs):
        nonlocal calls
        calls += 1
        return source

    options = Stage8ExperimentCliOptions(
        split=ExperimentSplit.DEVELOPMENT,
        public_ci_sha=CODE_SHA,
        confirm_public_ci_success=True,
        development_result=Path("tmp/stage8/development.json"),
        runs_root=Path("data/runs/evaluation/stage8_multi_agent"),
    )

    result = run_cli(
        options,
        repository_root=tmp_path,
        code_sha_reader=lambda root: CODE_SHA,
        experiment_runner=scripted_runner,
    )

    output = tmp_path / "tmp/stage8/development.json"
    assert result == source
    assert output.is_file()
    assert "scenario" not in output.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_cli(
            options,
            repository_root=tmp_path,
            code_sha_reader=lambda root: CODE_SHA,
            experiment_runner=scripted_runner,
        )
    assert calls == 1


def test_holdout_cli_refuses_before_any_runner_without_confirmation(
    tmp_path: Path,
) -> None:
    called = False

    def forbidden_runner(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("runner must not be called")

    options = Stage8ExperimentCliOptions(
        split=ExperimentSplit.HOLDOUT,
        public_ci_sha=CODE_SHA,
        confirm_public_ci_success=True,
        confirm_holdout=False,
    )

    with pytest.raises(RuntimeError, match="holdout requires confirmation"):
        run_cli(
            options,
            repository_root=tmp_path,
            code_sha_reader=lambda root: CODE_SHA,
            experiment_runner=forbidden_runner,
        )

    assert called is False


def test_cli_paths_cannot_escape_their_frozen_directories(tmp_path: Path) -> None:
    options = Stage8ExperimentCliOptions(
        split=ExperimentSplit.DEVELOPMENT,
        public_ci_sha=CODE_SHA,
        confirm_public_ci_success=True,
        development_result=Path("../escaped.json"),
    )

    with pytest.raises(ValueError, match="development result"):
        run_cli(
            options,
            repository_root=tmp_path,
            code_sha_reader=lambda root: CODE_SHA,
        )
