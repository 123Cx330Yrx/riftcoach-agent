from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.glm53_flash_response_profile_split import (
    DEFAULT_OUTPUT,
    EVIDENCE_ORIGIN,
    PROTOCOL_ID,
    RESPONSE_PROFILE_SPLIT_FIXTURE_CATALOG_SHA256,
    RESPONSE_PROFILE_SPLIT_FIXTURES,
    ResponseProfileSplitError,
    ResponseProfileSplitReceipt,
    canonical_receipt_bytes,
    run_response_profile_terminal_recovery_split,
    write_response_profile_terminal_recovery_receipt,
)


SHA = "a" * 40
DIAGNOSTIC_SHA = "b" * 40
PLAN_SHA = "c" * 40


def _receipt() -> ResponseProfileSplitReceipt:
    return run_response_profile_terminal_recovery_split(
        implementation_sha=SHA,
        diagnostic_code_sha=DIAGNOSTIC_SHA,
        input_plan_sha=PLAN_SHA,
    )


def test_fixed_matrix_separates_profile_terminal_usage_and_recovery() -> None:
    receipt = _receipt()

    assert receipt.protocol_id == PROTOCOL_ID
    assert receipt.evidence_origin == EVIDENCE_ORIGIN
    assert receipt.real_provider_observed is False
    assert receipt.provider_call_count == 0
    assert receipt.network_used is False
    assert receipt.all_cases_passed is True
    assert receipt.case_count == len(RESPONSE_PROFILE_SPLIT_FIXTURES) == 9
    assert receipt.fixture_catalog_sha256 == RESPONSE_PROFILE_SPLIT_FIXTURE_CATALOG_SHA256

    by_id = {case.case_id: case for case in receipt.cases}
    assert by_id["low-2048-complete-stop"].observed_state == "complete_text"
    assert by_id["max-8192-candidate-length"].candidate_disposition == "candidate_eligible"
    assert by_id["max-8192-candidate-length"].candidate_continuation_allowed is False
    assert by_id["max-8192-candidate-length"].recovery_action == "blocked_activation"
    assert by_id["max-8192-elapsed-before-terminal"].observed_error_code == "elapsed_limit"
    assert by_id["low-2048-terminal-without-usage"].observed_error_code == "usage_unavailable"
    assert by_id["max-8192-tool-calls-ready"].observed_state == "tool_calls_ready"


def test_receipt_is_canonical_round_trip_and_body_free() -> None:
    receipt = _receipt()
    payload = receipt.as_dict()
    encoded = canonical_receipt_bytes(receipt).decode("utf-8")

    assert ResponseProfileSplitReceipt.from_dict(payload).as_dict() == payload
    for private_value in (
        "private fixture reasoning",
        "private fixture answer",
        "fixture-call",
        "knowledge.search",
    ):
        assert private_value not in encoded
    for forbidden_key in (
        '"body"',
        '"content"',
        '"reasoning"',
        '"messages"',
        '"prompt"',
        '"request_id"',
    ):
        assert forbidden_key not in encoded


def test_writer_is_create_only_and_restricted_to_offline_root(tmp_path: Path) -> None:
    receipt = _receipt()
    offline_root = tmp_path / "offline"
    output = offline_root / "split.json"

    assert write_response_profile_terminal_recovery_receipt(
        output, receipt, offline_root=offline_root
    ) == output
    assert json.loads(output.read_text(encoding="utf-8")) == receipt.as_dict()
    with pytest.raises(FileExistsError):
        write_response_profile_terminal_recovery_receipt(
            output, receipt, offline_root=offline_root
        )
    with pytest.raises(ResponseProfileSplitError, match="offline_path_required"):
        write_response_profile_terminal_recovery_receipt(
            tmp_path / "outside.json", receipt, offline_root=offline_root
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("real_provider_observed", True),
        ("network_used", True),
        ("provider_call_count", 1),
        ("evidence_origin", "provider"),
        ("api_key", "secret"),
    ],
)
def test_receipt_rejects_provider_or_private_claims(field: str, value: object) -> None:
    payload = _receipt().as_dict()
    payload[field] = value
    with pytest.raises(ResponseProfileSplitError):
        ResponseProfileSplitReceipt.from_dict(payload)


def test_receipt_rejects_case_count_or_case_mutation() -> None:
    payload = _receipt().as_dict()
    payload["case_count"] = payload["case_count"] + 1  # type: ignore[operator]
    with pytest.raises(ResponseProfileSplitError, match="case_count"):
        ResponseProfileSplitReceipt.from_dict(payload)

    payload = _receipt().as_dict()
    payload["cases"] = [
        {**payload["cases"][0], "body": "private"},
        *payload["cases"][1:],
    ]
    with pytest.raises(ResponseProfileSplitError):
        ResponseProfileSplitReceipt.from_dict(payload)


def test_cli_replays_without_provider_or_environment(tmp_path: Path, capsys) -> None:
    import importlib.util

    path = Path(__file__).parents[1] / "scripts" / "replay_glm53_flash_response_profile_split.py"
    spec = importlib.util.spec_from_file_location("response_profile_split_cli", path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    output = tmp_path / "data" / "evaluation" / "results" / "offline" / "split.json"

    assert cli.main(
        [
            "--repository-root",
            str(tmp_path),
            "--implementation-sha",
            SHA,
            "--diagnostic-code-sha",
            DIAGNOSTIC_SHA,
            "--input-plan-sha",
            PLAN_SHA,
            "--output",
            str(output),
        ]
    ) == 0
    assert "provider_calls=0" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["network_used"] is False


def test_default_output_stays_in_offline_results_tree() -> None:
    assert str(DEFAULT_OUTPUT).replace("\\", "/").startswith(
        "data/evaluation/results/offline/"
    )
