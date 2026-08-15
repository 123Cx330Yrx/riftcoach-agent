from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from app.evaluation.provider_resource_calibration import (
    ResourceCalibrationAdmission,
    capture_resource_calibration_requests,
    load_resource_calibration_profiles,
    prepare_resource_calibration_admission,
)
from tests.test_provider_resource_calibration import (
    OfflineFakeCalibrationProvider,
    PROFILES,
    ROOT,
    StepClock,
    V2_PROTECTED,
)
from scripts.run_deepseek_resource_calibration import (
    DeepSeekResourceCalibrationCliOptions,
    ResourceCalibrationPreparedRun,
    ResourceCalibrationRunOutput,
    run_cli,
)


def prepared_run() -> ResourceCalibrationPreparedRun:
    loaded = load_resource_calibration_profiles(
        PROFILES,
        project_root=ROOT,
        protected_paths=V2_PROTECTED,
    )
    with tempfile.TemporaryDirectory() as directory:
        frozen = capture_resource_calibration_requests(
            loaded,
            project_root=ROOT,
            runs_root=directory,
        )
    admission = prepare_resource_calibration_admission(
        loaded=loaded,
        frozen_requests=frozen,
        code_sha="a" * 40,
        public_ci_sha="a" * 40,
        public_ci_success_confirmed=True,
    )
    return ResourceCalibrationPreparedRun(
        admission=admission,
        frozen_requests=frozen,
    )


def options(**updates) -> DeepSeekResourceCalibrationCliOptions:
    values = {
        "confirm_real_call": True,
        "confirm_public_ci_success": True,
        "public_ci_sha": "a" * 40,
        "prepare_only": False,
        "max_calls": 8,
        "output": Path(
            "data/evaluation/results/provider_capabilities/"
            "resource_calibration.json"
        ),
        "budget_output": Path(
            "data/evaluation/results/provider_capabilities/"
            "resource_budget.json"
        ),
    }
    values.update(updates)
    return DeepSeekResourceCalibrationCliOptions(**values)


def test_prepare_only_stops_before_reservation_environment_and_provider(
    tmp_path: Path,
) -> None:
    events = []

    admission = run_cli(
        options(prepare_only=True, confirm_real_call=False),
        repository_root=tmp_path,
        preflight_runner=lambda **kwargs: (
            events.append("preflight") or prepared_run()
        ),
        environment_loader=lambda root: events.append("environment"),
        provider_factory=lambda settings: events.append("provider"),
    )

    assert isinstance(admission, ResourceCalibrationAdmission)
    assert events == ["preflight"]
    assert not (tmp_path / options().output).exists()


def test_real_cli_is_key_last_and_writes_sanitized_result_and_budget(
    tmp_path: Path,
) -> None:
    events = []
    output = tmp_path / options().output

    def preflight(**kwargs):
        events.append("preflight")
        return prepared_run()

    def environment(root):
        events.append("environment")
        assert output.exists()
        return {"DEEPSEEK_API_KEY": "sk-RAW-CALIBRATION-KEY"}

    def provider(settings):
        events.append("provider")
        assert settings.api_key == "sk-RAW-CALIBRATION-KEY"
        return OfflineFakeCalibrationProvider(
            usages=((100, 1),) * 8,
            is_offline_calibration_fake=False,
        )

    outcome = run_cli(
        options(),
        repository_root=tmp_path,
        preflight_runner=preflight,
        environment_loader=environment,
        provider_factory=provider,
        clock=StepClock(),
    )

    assert isinstance(outcome, ResourceCalibrationRunOutput)
    assert events == ["preflight", "environment", "provider"]
    assert outcome.result.status == "completed"
    assert outcome.result.external_provider_calls == 8
    assert outcome.budget is not None
    result_bytes = output.read_bytes()
    budget_bytes = (tmp_path / options().budget_output).read_bytes()
    assert outcome.budget.calibration_result_sha256 == hashlib.sha256(
        result_bytes
    ).hexdigest()
    for forbidden in (
        b"sk-RAW-CALIBRATION-KEY",
        b"offline calibration response",
        b"raw-fake-request",
    ):
        assert forbidden not in result_bytes
        assert forbidden not in budget_bytes
    assert json.loads(result_bytes)["external_provider_calls"] == 8


def test_stopped_real_cli_commits_failure_and_does_not_create_budget(
    tmp_path: Path,
) -> None:
    provider = OfflineFakeCalibrationProvider(
        usages=((100, 1),) * 8,
        fail_at=3,
        is_offline_calibration_fake=False,
    )

    outcome = run_cli(
        options(),
        repository_root=tmp_path,
        preflight_runner=lambda **kwargs: prepared_run(),
        environment_loader=lambda root: {"DEEPSEEK_API_KEY": "hidden"},
        provider_factory=lambda settings: provider,
        clock=StepClock(),
    )

    assert outcome.result.status == "stopped"
    assert outcome.result.external_provider_calls == 3
    assert outcome.budget is None
    assert (tmp_path / options().output).exists()
    assert not (tmp_path / options().budget_output).exists()
    assert len(provider.requests) == 3


def test_confirmation_limits_and_output_conflict_stop_before_preflight(
    tmp_path: Path,
) -> None:
    calls = []
    preflight = lambda **kwargs: calls.append("preflight")

    with pytest.raises(RuntimeError, match="explicit confirmation"):
        run_cli(
            options(confirm_real_call=False),
            repository_root=tmp_path,
            preflight_runner=preflight,
        )
    with pytest.raises(ValueError, match="exactly 8 calls"):
        run_cli(
            options(max_calls=7),
            repository_root=tmp_path,
            preflight_runner=preflight,
        )

    existing = tmp_path / options().output
    existing.parent.mkdir(parents=True)
    existing.write_text("immutable", encoding="utf-8")
    with pytest.raises(FileExistsError, match="immutable"):
        run_cli(
            options(),
            repository_root=tmp_path,
            preflight_runner=preflight,
        )
    assert calls == []
