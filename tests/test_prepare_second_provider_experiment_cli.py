from pathlib import Path
import socket

import pytest

from app.evaluation.provider_adoption import (
    ExperimentFailureCode,
    ProviderExperimentPreparationError,
    prepare_second_provider_experiment,
)
from scripts.prepare_second_provider_experiment import (
    NoIoExperimentOptions,
    run_cli,
)


ROOT = Path(__file__).resolve().parents[1]
HELD_OUT = ROOT / "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
DEVELOPMENT = (
    ROOT
    / "data/evaluation/domain_e2e_v1_1_secure_executable_development_cases.json"
)
SNAPSHOT = (
    ROOT / "data/evaluation/contracts/recent_form_prompt_context_v1_1.json"
)
CODE_SHA = "a" * 40


def prepare(**updates):
    values = {
        "project_root": ROOT,
        "dataset_path": HELD_OUT,
        "snapshot_path": SNAPSHOT,
        "code_sha": CODE_SHA,
        "public_ci_sha": CODE_SHA,
        "confirm_public_ci_success": True,
    }
    values.update(updates)
    return prepare_second_provider_experiment(**values)


def test_prepares_exact_frozen_experiment_without_execution():
    report = prepare()

    assert report.provider_id == "deepseek"
    assert report.requested_model == "deepseek-v4-pro"
    assert report.base_url == "https://api.deepseek.com"
    assert report.sdk_max_retries == 0
    assert report.stream is False
    assert report.thinking == "disabled"
    assert report.protocol_max_calls == 3
    assert report.domain_max_calls == 12
    assert report.cumulative_max_calls == 15
    assert report.maximum_total_tokens == 16_000
    assert report.maximum_output_tokens_per_request == 1024
    assert str(report.maximum_estimated_cost) == "0.10"
    assert report.external_provider_calls == 0
    assert report.held_out_executed is False
    assert report.local_preflight_passed is True
    serialized = report.model_dump_json()
    for forbidden in (
        "api_key",
        "deepseek_api_key",
        "safe fixture",
        "model_output",
        "tool_observation",
        "canary",
        "request_id",
        "exception",
    ):
        assert forbidden not in serialized.lower()


@pytest.mark.parametrize(
    "updates",
    (
        {"provider_id": "zhipu"},
        {"model": "deepseek-v4-flash"},
        {"base_url": "https://example.invalid"},
        {"sdk_max_retries": 1},
    ),
)
def test_configuration_drift_fails_before_experiment_preparation(updates):
    with pytest.raises(ProviderExperimentPreparationError) as captured:
        prepare(**updates)

    assert captured.value.code is (
        ExperimentFailureCode.PROVIDER_CONFIGURATION_INVALID
    )


def test_public_ci_sha_or_confirmation_mismatch_fails_closed():
    with pytest.raises(ProviderExperimentPreparationError) as mismatch:
        prepare(public_ci_sha="b" * 40)
    assert mismatch.value.code is ExperimentFailureCode.PUBLIC_CI_SHA_MISMATCH

    with pytest.raises(ProviderExperimentPreparationError) as unconfirmed:
        prepare(confirm_public_ci_success=False)
    assert unconfirmed.value.code is (
        ExperimentFailureCode.PUBLIC_CI_SHA_MISMATCH
    )


def test_development_dataset_cannot_be_substituted_for_held_out():
    with pytest.raises(ProviderExperimentPreparationError) as captured:
        prepare(dataset_path=DEVELOPMENT)

    assert captured.value.code is ExperimentFailureCode.DATASET_NOT_FROZEN


def test_cli_dry_run_does_not_use_network_or_environment_key(monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network must not be used by no-I/O dry-run")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    report = run_cli(
        NoIoExperimentOptions(
            public_ci_sha=CODE_SHA,
            confirm_public_ci_success=True,
        ),
        repository_root=ROOT,
        code_sha_reader=lambda root: CODE_SHA,
    )

    assert report.external_provider_calls == 0
    assert report.held_out_executed is False
