from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.candidate_transport_gate import (
    CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID,
    CANDIDATE_TRANSPORT_GATE_SCHEMA_VERSION,
    CandidateTransportGateError,
    CandidateTransportGateReceipt,
    candidate_transport_gate_fixture_sha256,
    project_transport_gate_case,
    run_offline_transport_gate_case,
    run_offline_transport_gate_replay,
    write_candidate_transport_gate_receipt,
)


SHA = "a" * 40
OBSERVER_SHA = "b" * 40
PLAN_SHA = "c" * 40


def test_fixture_descriptor_has_stable_digest() -> None:
    digest = candidate_transport_gate_fixture_sha256()
    assert digest == "cc879340cab3275cea5db9b210d71fe2b88947bfe2c1375ddf5ac7c6c06cd366"


@pytest.mark.parametrize(
    ("phase", "expected_categories"),
    [
        ("after_first_event", ("reasoning_seen", "content_seen")),
        ("before_first_event", ()),
    ],
)
def test_sdk_transport_gate_reaches_pending_read_without_network(
    phase: str,
    expected_categories: tuple[str, ...],
) -> None:
    observation, metrics = run_offline_transport_gate_case(phase)

    assert observation.pending_reader_observed is True
    assert observation.reader_woke is True
    assert observation.cancel_returned is True
    assert tuple(observation.event_categories) == expected_categories
    assert metrics.transport_request_count == 1
    assert metrics.upstream_event_seen is True
    assert metrics.gate_entered is True
    assert metrics.gate_released is False
    assert metrics.downstream_close_seen is True
    assert metrics.upstream_stream_close_seen is True
    # The reader wake and cleanup projection are intentionally independent.
    assert observation.close_report.composite_state in {"closed", "failed"}


def test_replay_receipt_is_body_free_and_round_trips() -> None:
    receipt = run_offline_transport_gate_replay(
        implementation_sha=SHA,
        observer_code_sha=OBSERVER_SHA,
        input_plan_sha=PLAN_SHA,
    )

    assert receipt.all_cases_passed is True
    payload = receipt.as_dict()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert "fixture reasoning" not in encoded
    assert "fixture answer" not in encoded
    assert payload["evidence_origin"] == "offline_sdk_transport_fixture"
    assert payload["provider_call_count"] == 0
    assert payload["network_used"] is False
    restored = CandidateTransportGateReceipt.from_dict(payload)
    assert restored.as_dict() == payload


def test_projection_classifies_wakeup_and_close_race_separately() -> None:
    observation, metrics = run_offline_transport_gate_case("after_first_event")
    case = project_transport_gate_case(
        "after-first-event",
        "after_first_event",
        observation,
        metrics,
    )

    assert case.passed is True
    assert case.reader_woke is True
    assert case.conclusion in {"client_wakeup_clean", "client_wakeup_close_race"}
    assert case.close_report["composite_state"] in {"closed", "failed"}


def test_receipt_writer_is_immutable_and_stays_under_offline_root(tmp_path: Path) -> None:
    receipt = run_offline_transport_gate_replay(
        implementation_sha=SHA,
        observer_code_sha=OBSERVER_SHA,
        input_plan_sha=PLAN_SHA,
    )
    output = tmp_path / "offline" / "receipt.json"
    written = write_candidate_transport_gate_receipt(
        output,
        receipt,
        offline_root=tmp_path / "offline",
    )
    assert written == output
    with pytest.raises(FileExistsError):
        write_candidate_transport_gate_receipt(
            output,
            receipt,
            offline_root=tmp_path / "offline",
        )


def test_receipt_writer_rejects_path_outside_offline_root(tmp_path: Path) -> None:
    receipt = run_offline_transport_gate_replay(
        implementation_sha=SHA,
        observer_code_sha=OBSERVER_SHA,
        input_plan_sha=PLAN_SHA,
    )
    with pytest.raises(CandidateTransportGateError):
        write_candidate_transport_gate_receipt(
            tmp_path / "outside.json",
            receipt,
            offline_root=tmp_path / "offline",
        )


def test_receipt_contract_has_distinct_protocol_and_schema() -> None:
    receipt = run_offline_transport_gate_replay(
        implementation_sha=SHA,
        observer_code_sha=OBSERVER_SHA,
        input_plan_sha=PLAN_SHA,
    )
    assert receipt.protocol_id == CANDIDATE_TRANSPORT_GATE_PROTOCOL_ID
    assert receipt.schema_version == CANDIDATE_TRANSPORT_GATE_SCHEMA_VERSION
