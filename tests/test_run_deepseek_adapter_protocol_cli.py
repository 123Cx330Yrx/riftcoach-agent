from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.provider_adoption import ExperimentPreparationReport
from tests.test_deepseek_protocol_experiment import successful_provider
from scripts.run_deepseek_adapter_protocol import (
    DeepSeekProtocolCliOptions,
    run_cli,
)


def preparation() -> ExperimentPreparationReport:
    return ExperimentPreparationReport(
        provider_id="deepseek",
        requested_model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        sdk_max_retries=0,
        stream=False,
        thinking="disabled",
        code_sha="a" * 40,
        public_ci_sha="a" * 40,
        public_ci_success_confirmed=True,
        dataset_id="domain-e2e-v1-1-secure-held-out",
        dataset_version="1.0.0",
        dataset_sha256="b" * 64,
        prompt_context_snapshot_id="recent-form-prompt-context-v1-1",
        prompt_context_snapshot_sha256="c" * 64,
        evaluation_contract="coach_evaluation@1.1.0",
        protocol_max_calls=3,
        domain_max_calls=12,
        cumulative_max_calls=15,
        maximum_total_tokens=16_000,
        maximum_output_tokens_per_request=1024,
        maximum_estimated_cost="0.10",
        currency="USD",
        external_provider_calls=0,
        held_out_executed=False,
        local_preflight_passed=True,
    )


def options(output: Path, **updates) -> DeepSeekProtocolCliOptions:
    values = {
        "confirm_real_call": True,
        "confirm_public_ci_success": True,
        "public_ci_sha": "a" * 40,
        "max_calls": 3,
        "output": output,
    }
    values.update(updates)
    return DeepSeekProtocolCliOptions(**values)


def test_missing_real_call_confirmation_stops_before_preflight(tmp_path) -> None:
    calls = []

    with pytest.raises(RuntimeError, match="explicit confirmation"):
        run_cli(
            options(
                Path("data/evaluation/results/provider_capabilities/result.json"),
                confirm_real_call=False,
            ),
            repository_root=tmp_path,
            preflight_runner=lambda *args, **kwargs: calls.append("preflight"),
            provider_factory=lambda settings: calls.append("provider"),
        )

    assert calls == []


def test_preflight_failure_stops_before_environment_or_provider(tmp_path) -> None:
    calls = []

    def fail_preflight(*args, **kwargs):
        calls.append("preflight")
        raise RuntimeError("safe preflight failure")

    with pytest.raises(RuntimeError, match="safe preflight failure"):
        run_cli(
            options(
                Path("data/evaluation/results/provider_capabilities/result.json")
            ),
            repository_root=tmp_path,
            preflight_runner=fail_preflight,
            environment_loader=lambda root: calls.append("environment"),
            provider_factory=lambda settings: calls.append("provider"),
        )

    assert calls == ["preflight"]


def test_success_writes_only_sanitized_record_after_preflight(tmp_path) -> None:
    relative_output = Path(
        "data/evaluation/results/provider_capabilities/deepseek_result.json"
    )
    events = []

    def preflight(*args, **kwargs):
        events.append("preflight")
        return preparation()

    def load_environment(root):
        events.append("environment")
        return {"DEEPSEEK_API_KEY": "sk-RAW-KEY"}

    def create_provider(settings):
        events.append("provider")
        assert settings.api_key == "sk-RAW-KEY"
        return successful_provider()

    record = run_cli(
        options(relative_output),
        repository_root=tmp_path,
        preflight_runner=preflight,
        environment_loader=load_environment,
        provider_factory=create_provider,
    )

    assert events == ["preflight", "environment", "provider"]
    assert record.protocol.admitted is True
    payload = (tmp_path / relative_output).read_text(encoding="utf-8")
    assert json.loads(payload)["protocol"]["calls_used"] == 3
    assert "sk-RAW-KEY" not in payload
    assert "RAW_REQUEST_ID" not in payload


def test_existing_or_outside_output_fails_before_preflight(tmp_path) -> None:
    inside = (
        tmp_path
        / "data/evaluation/results/provider_capabilities/existing.json"
    )
    inside.parent.mkdir(parents=True)
    inside.write_text("immutable", encoding="utf-8")
    calls = []

    with pytest.raises(FileExistsError):
        run_cli(
            options(inside),
            repository_root=tmp_path,
            preflight_runner=lambda *args, **kwargs: calls.append("preflight"),
        )
    assert calls == []

    with pytest.raises(ValueError, match="result directory"):
        run_cli(
            options(tmp_path / "outside.json"),
            repository_root=tmp_path,
            preflight_runner=lambda *args, **kwargs: calls.append("preflight"),
        )
    assert calls == []
