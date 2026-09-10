from __future__ import annotations

import pytest

from app.evaluation.coach_real_data_golden_slice import GoldenSliceConfig, preflight


def test_golden_slice_preflight_is_network_free_and_freezes_budget() -> None:
    gate = preflight(
        GoldenSliceConfig(
            riot_id="DK ShowMaker#KR1",
            routing_region="asia",
            count=5,
            position="mid",
            run_id="golden_20260910_showmaker",
        )
    )
    assert gate.network_allowed is False
    assert gate.max_riot_calls == 12
    assert gate.max_ddragon_requests == 5
    assert gate.max_opgg_tool_calls == 5
    assert gate.max_opgg_session_initializations == 5
    assert gate.max_opgg_catalog_requests == 5
    assert gate.position == "auto"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("routing_region", "kr", "routing_region_invalid"),
        ("position", "unknown", "position_invalid"),
        ("queue", 430, "queue_not_admitted"),
    ],
)
def test_golden_slice_preflight_rejects_unbounded_or_unadmitted_inputs(field, value, error):
    values = {
        "riot_id": "DK ShowMaker#KR1",
        "routing_region": "asia",
        "count": 5,
        "position": "mid",
        "run_id": "golden_20260910_showmaker",
    }
    values[field] = value
    with pytest.raises(ValueError, match=f"^{error}$"):
        preflight(GoldenSliceConfig(**values))


def test_opgg_fetches_actual_roles_once_and_not_training_goal():
    from app.product.coach_positions import position_context
    from app.evaluation.coach_real_data_golden_slice import _collect_position_meta
    from tests.test_opgg_meta_adapter import make_adapter
    from dataclasses import replace

    base, _ = make_adapter()
    evidence = base.fetch(position="top")
    context = position_context({"matches": [
        {"role": "MIDDLE", "champion_name_en": "Nasus", "included_in_aggregate": True},
        {"role": "MIDDLE", "champion_name_en": "Nasus", "included_in_aggregate": True},
        {"role": "UTILITY", "champion_name_en": "Anivia", "included_in_aggregate": True},
    ]}, training_positions=("jungle",))
    calls = []

    def fetch(**kwargs):
        calls.append(kwargs)
        return replace(evidence, position=kwargs["position"])

    meta, coverage = _collect_position_meta(context, fetch)
    assert [call["position"] for call in calls] == ["mid", "support"]
    assert calls[0]["target_champions"] == ("Nasus",)
    assert len(meta) == 1
    assert meta[0].position == "mid"
    assert len(meta[0].facts) == 1
    assert coverage[0]["status"] == "matched"
    assert coverage[1]["status"] == "target_not_in_response"
    assert coverage[1]["unmatched_champions"] == ("Anivia",)


def test_opgg_request_failure_and_wrong_lane_are_distinct():
    from app.product.coach_positions import position_context
    from app.evaluation.coach_real_data_golden_slice import _collect_position_meta
    from tests.test_opgg_meta_adapter import make_adapter
    adapter, _ = make_adapter()
    evidence = adapter.fetch(position="top")
    context = position_context({"matches": [
        {"role": "mid", "champion_name_en": "Nasus", "included_in_aggregate": True},
    ]})
    _, coverage = _collect_position_meta(context, lambda **_: evidence)
    assert coverage[0]["status"] == "invalid_response"

    def fail(**_):
        raise RuntimeError("private upstream response")

    _, coverage = _collect_position_meta(context, fail)
    assert coverage[0]["status"] == "request_failed"
    assert "private" not in str(coverage)


def test_real_entry_uses_actual_role_queries_with_no_network(monkeypatch):
    import copy
    import json
    import socket
    import app.evaluation.coach_real_data_golden_slice as module

    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(module, "_assert_clean_tree", lambda: None)
    monkeypatch.setattr(module, "_implementation_sha", lambda: "a" * 40)
    monkeypatch.setattr(module, "RiotClient", lambda **_: object())
    monkeypatch.setattr(module, "DataDragonService", lambda **_: object())
    from tests.test_evidence_summary_bridge import summary as make_summary
    summary = make_summary()
    summary["matches"][0]["role"] = "MIDDLE"
    summary["matches"][1]["role"] = "UTILITY"
    monkeypatch.setattr(module, "build_player_summary", lambda **_: copy.deepcopy(summary))
    monkeypatch.setattr(module, "_ddragon_snapshot", lambda *args: None)
    monkeypatch.setattr(module, "_official_patch", lambda **_: None)
    calls = []

    def missing(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("fixture missing source")

    receipt = module.run_golden_slice(module.GoldenSliceConfig(
        riot_id="RiftCoachDemo#TEST", routing_region="asia", run_id="roles_offline_001",
        position="mid", training_positions=("jungle",),
    ), environ={"RIOT_API_KEY": "fake-offline-key"}, opgg_fetcher=missing)
    assert [call["position"] for call in calls] == ["mid", "support"]
    assert receipt.position_context.training_positions == ("jungle",)
    assert receipt.result == "degraded"
    assert receipt.provider_calls == 0
    assert "opgg_target_coverage_incomplete" in receipt.limitations
    assert "training_persistence_not_verified" in receipt.limitations
    assert "live_workbench_not_verified" in receipt.limitations
