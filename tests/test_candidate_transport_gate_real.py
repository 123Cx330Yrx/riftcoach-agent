from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.candidate_transport_gate import run_offline_transport_gate_case
from app.evaluation.candidate_transport_gate_real import (
    CandidateRealTransportGateError,
    CandidateRealTransportGateReceipt,
    build_real_transport_gate_receipt,
    default_transport_metrics,
    safe_child_observation,
    write_real_transport_gate_receipt,
)


def _receipt() -> CandidateRealTransportGateReceipt:
    observation, metrics = run_offline_transport_gate_case("before_first_event")
    return build_real_transport_gate_receipt(
        implementation_sha="a" * 40,
        observer_code_sha="b" * 40,
        input_plan_sha="c" * 40,
        gate_phase="before_first_event",
        process_deadline_ms=30_000,
        observation=observation,
        metrics=metrics,
        provider_call_count=1,
    )


def test_real_receipt_projects_one_call_and_round_trips_without_body() -> None:
    receipt = _receipt()
    payload = receipt.as_dict()
    assert receipt.real_provider_observed is True
    assert receipt.network_used is True
    assert receipt.provider_call_count == 1
    assert receipt.gate_observation_valid is True
    assert CandidateRealTransportGateReceipt.from_dict(payload).as_dict() == payload
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "fixture answer" not in encoded
    assert "api_key" not in encoded


def test_real_receipt_rejects_count_or_forbidden_field_drift() -> None:
    payload = _receipt().as_dict()
    payload["transport_request_count"] = 0
    with pytest.raises(CandidateRealTransportGateError):
        CandidateRealTransportGateReceipt.from_dict(payload)

    payload = _receipt().as_dict()
    payload["observation"]["response_body"] = "must not persist"
    with pytest.raises(CandidateRealTransportGateError):
        CandidateRealTransportGateReceipt.from_dict(payload)


def test_real_receipt_writer_is_create_only_and_scope_bound(tmp_path: Path) -> None:
    receipt = _receipt()
    results_root = tmp_path / "provider_capabilities"
    output = results_root / "result.json"
    assert write_real_transport_gate_receipt(
        output,
        receipt,
        results_root=results_root,
    ) == output
    with pytest.raises(FileExistsError):
        write_real_transport_gate_receipt(output, receipt, results_root=results_root)
    with pytest.raises(CandidateRealTransportGateError):
        write_real_transport_gate_receipt(
            tmp_path / "outside.json",
            receipt,
            results_root=results_root,
        )


def test_safe_child_fallback_is_zero_call_and_body_free() -> None:
    observation = safe_child_observation("child_timeout", terminated=True)
    receipt = build_real_transport_gate_receipt(
        implementation_sha="a" * 40,
        observer_code_sha="b" * 40,
        input_plan_sha="c" * 40,
        gate_phase="before_first_event",
        process_deadline_ms=30_000,
        observation=observation,
        metrics=default_transport_metrics(),
        provider_call_count=0,
    )
    assert receipt.conclusion == "child_timeout"
    assert receipt.gate_observation_valid is False
    assert receipt.real_provider_observed is False
