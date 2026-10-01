from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.candidate_close_wakeup_replay import (
    CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID,
    CANDIDATE_CLOSE_WAKE_REPLAY_SCHEMA_VERSION,
    CANDIDATE_CLOSE_WAKE_REPLAY_SCENARIO_SHA256,
    CandidateCloseWakeReplayError,
    CandidateCloseWakeReplayReceipt,
    REPLAY_EVIDENCE_ORIGIN,
    REPLAY_SCENARIOS,
    run_candidate_close_wakeup_replay,
    write_candidate_close_wakeup_replay_receipt,
)


SHA = "a" * 40
OBSERVER_SHA = "b" * 40
PLAN_SHA = "c" * 40


def _receipt() -> CandidateCloseWakeReplayReceipt:
    return run_candidate_close_wakeup_replay(
        implementation_sha=SHA,
        observer_code_sha=OBSERVER_SHA,
        input_plan_sha=PLAN_SHA,
    )


def test_fixed_replay_matrix_covers_core_lifecycle_without_provider_calls():
    receipt = _receipt()

    assert receipt.protocol_id == CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID
    assert receipt.schema_version == CANDIDATE_CLOSE_WAKE_REPLAY_SCHEMA_VERSION
    assert receipt.evidence_origin == REPLAY_EVIDENCE_ORIGIN
    assert receipt.real_provider_observed is False
    assert receipt.provider_call_count == 0
    assert receipt.network_used is False
    assert receipt.all_cases_passed is True
    assert tuple(case.scenario_id for case in receipt.cases) == tuple(
        scenario.scenario_id for scenario in REPLAY_SCENARIOS
    )
    assert {case.observed_observation_state for case in receipt.cases} == {
        "not_pending",
        "pending_cancel_returned",
        "pending_cancel_timeout",
    }
    assert {case.observed_cancel_status for case in receipt.cases} == {
        "not_attempted",
        "returned",
        "timeout",
        "raised",
    }
    assert all(case.observer_call_count == 1 for case in receipt.cases)
    assert all(case.fake_session_open_count == 1 for case in receipt.cases)


def test_replay_has_stable_scenario_digest_and_canonical_bytes():
    first = _receipt()
    second = _receipt()

    assert first.as_dict() == second.as_dict()
    assert first.scenario_sha256 == CANDIDATE_CLOSE_WAKE_REPLAY_SCENARIO_SHA256
    encoded = json.dumps(
        first.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    assert encoded.endswith(b"\n")


def test_replay_receipt_round_trip_and_writer_is_create_only(tmp_path: Path):
    receipt = _receipt()
    offline_root = tmp_path / "offline"
    output = offline_root / "replay.json"

    written = write_candidate_close_wakeup_replay_receipt(
        output, receipt, offline_root=offline_root
    )
    assert written == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert CandidateCloseWakeReplayReceipt.from_dict(payload).as_dict() == payload
    with pytest.raises(FileExistsError, match="immutable"):
        write_candidate_close_wakeup_replay_receipt(
            output, receipt, offline_root=offline_root
        )
    with pytest.raises(CandidateCloseWakeReplayError, match="offline_path_required"):
        write_candidate_close_wakeup_replay_receipt(
            tmp_path / "provider_capabilities" / "wrong.json",
            receipt,
            offline_root=offline_root,
        )


@pytest.mark.parametrize(
    "output",
    [
        Path("outside.json"),
        Path("offline/not-json.txt"),
        Path("offline/provider_capabilities/wrong.json"),
    ],
)
def test_replay_writer_enforces_explicit_offline_root(tmp_path: Path, output: Path):
    offline_root = tmp_path / "offline"
    with pytest.raises(CandidateCloseWakeReplayError, match="offline_path_required"):
        write_candidate_close_wakeup_replay_receipt(
            tmp_path / output,
            _receipt(),
            offline_root=offline_root,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("evidence_origin", "provider"),
        ("real_provider_observed", True),
        ("provider_call_count", 1),
        ("network_used", True),
        ("scenario_sha256", "bad"),
        ("api_key", "secret"),
    ],
)
def test_replay_receipt_rejects_provider_or_body_claims(field, value):
    payload = _receipt().as_dict()
    if field == "api_key":
        payload[field] = value
    else:
        payload[field] = value
    with pytest.raises(CandidateCloseWakeReplayError):
        CandidateCloseWakeReplayReceipt.from_dict(payload)


def test_replay_receipt_rejects_extra_case_and_scenario_fields():
    receipt = _receipt()
    payload = receipt.as_dict()
    payload["cases"] = [
        {**payload["cases"][0], "body": "private"},
        *payload["cases"][1:],
    ]
    with pytest.raises(CandidateCloseWakeReplayError):
        CandidateCloseWakeReplayReceipt.from_dict(payload)

    scenario = REPLAY_SCENARIOS[0].as_dict()
    with pytest.raises(CandidateCloseWakeReplayError):
        REPLAY_SCENARIOS[0].from_dict({**scenario, "extra": True})


def test_replay_does_not_reuse_real_provider_protocol_or_claim_provider_calls():
    receipt = _receipt()
    rendered = json.dumps(receipt.as_dict(), ensure_ascii=False)
    assert CANDIDATE_CLOSE_WAKE_REPLAY_PROTOCOL_ID in rendered
    assert "glm-5.3-flash-candidate-close-wakeup-observation" not in rendered
    assert '"provider_call_count":0' in rendered.replace(" ", "")
    assert "private fixture control text" not in rendered


def test_replay_cli_writes_offline_receipt_without_confirmation_or_environment(
    tmp_path: Path,
    capsys,
    monkeypatch,
):
    import importlib.util

    script_path = Path(__file__).parents[1] / "scripts" / "replay_glm53_flash_candidate_close_wakeup.py"
    spec = importlib.util.spec_from_file_location("candidate_close_replay_cli", script_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    class ForbiddenProviderClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("offline replay must not construct a provider client")

    # The package import may already have loaded the SDK dependency.  Replacing
    # the client constructor proves the stronger boundary we actually promise:
    # this command never instantiates or invokes it.
    import app.providers.config as provider_config

    monkeypatch.setattr(provider_config, "OpenAI", ForbiddenProviderClient)

    output = tmp_path / "data" / "evaluation" / "results" / "offline" / "replay.json"
    assert cli.main(
        [
            "--repository-root",
            str(tmp_path),
            "--implementation-sha",
            SHA,
            "--observer-code-sha",
            OBSERVER_SHA,
            "--input-plan-sha",
            PLAN_SHA,
            "--output",
            str(output),
        ]
    ) == 0
    assert "provider_calls=0" in capsys.readouterr().out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_origin"] == "offline_fake"
    assert payload["real_provider_observed"] is False


def test_replay_cli_rejects_non_offline_output_path(tmp_path: Path, capsys):
    import importlib.util

    script_path = Path(__file__).parents[1] / "scripts" / "replay_glm53_flash_candidate_close_wakeup.py"
    spec = importlib.util.spec_from_file_location("candidate_close_replay_cli_path", script_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    assert cli.main(
        [
            "--repository-root",
            str(tmp_path),
            "--implementation-sha",
            SHA,
            "--observer-code-sha",
            OBSERVER_SHA,
            "--input-plan-sha",
            PLAN_SHA,
            "--output",
            str(tmp_path / "not-offline" / "replay.json"),
        ]
    ) == 2
    assert "output_path_invalid" in capsys.readouterr().err
