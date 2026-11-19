import copy
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from app.evaluation.coach_real_data_golden_slice import GoldenSliceConfig, preflight, run_golden_slice
from app.evaluation.golden_saved_input import load_saved_summary, refresh_saved_static
from tests.test_coach_application_composition import dependencies


def config(**kwargs):
    return GoldenSliceConfig(riot_id="Offline#TEST", routing_region="asia", run_id="saved_replay_new",
        saved_run_id="saved_replay_old", saved_summary_digest="a" * 64, **kwargs)


def test_saved_preflight_freezes_zero_riot_calls_and_source_identity():
    gate = preflight(config())
    assert gate.max_riot_calls == 0 and not gate.network_allowed
    assert gate.saved_run_id == "saved_replay_old" and gate.saved_summary_digest == "a" * 64
    from dataclasses import replace
    for change in [{"saved_summary_digest": None}, {"saved_run_id": "../other"},
                   {"saved_run_id": "saved_replay_new"}, {"saved_summary_digest": "not-a-digest"}]:
        with pytest.raises(ValueError, match="saved_golden"):
            preflight(replace(config(), **change))


def test_saved_entry_requires_no_riot_key_client_or_match_fetch(tmp_path, monkeypatch):
    import app.evaluation.coach_real_data_golden_slice as module
    import app.evaluation.golden_saved_input as saved
    summary = copy.deepcopy(dependencies()["summary_builder"].summary)
    for i, row in enumerate(summary["matches"]):
        row.update(game_version="16.17.100.1", queue_id=420, champion_id=i + 1)
    observed = datetime.fromisoformat(summary["metadata"]["generated_at_utc"].replace("Z", "+00:00"))
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_assert_clean_tree", lambda: None)
    monkeypatch.setattr(module, "_implementation_sha", lambda: "a" * 40)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved replay must not access Riot")
    monkeypatch.setattr(module, "RiotClient", forbidden)
    monkeypatch.setattr(module, "build_player_summary", forbidden)
    monkeypatch.setattr(saved, "load_saved_summary", lambda *args, **kwargs: (copy.deepcopy(summary), observed))
    service = SimpleNamespace(version="16.17.1", language="zh_CN",
        enrich_match_row=lambda row: row, enrich_item_purchases=lambda rows: rows)
    monkeypatch.setattr(module, "GoldenMatchStaticData", lambda **kwargs: service)
    monkeypatch.setattr(module, "_official_patch", lambda **kwargs: None)
    monkeypatch.setattr(module, "_ddragon_snapshot", lambda *args: None)
    receipt = run_golden_slice(config(), environ={}, opgg_fetcher=lambda **kwargs: None)
    assert receipt.result == "degraded" and receipt.provider_calls == 0
    path = tmp_path / "data/runs/golden_slice_reservations/saved_replay_new/terminal.json"
    assert json.loads(path.read_text(encoding="utf-8"))["attempt_counts"]["riot"] == 0


def test_refresh_replaces_static_names_and_preserves_match_measurements():
    original = {"request": {"data_dragon_version": "16.18.1"}, "matches": [
        {"game_version": "16.17.100.1", "role": "UTILITY", "gold_earned": 5000,
         "champion_name": "old", "timeline_available": True,
         "item_purchases": [{"item_id": 1, "timestamp": 100, "item_name": "old"}]}]}
    def enrich(row):
        row["champion_name"] = "correct"
    def purchases(rows):
        rows[0]["item_name"] = "correct"
    actual = refresh_saved_static(copy.deepcopy(original), SimpleNamespace(
        version="16.17.1", language="zh_CN", enrich_match_row=enrich, enrich_item_purchases=purchases))
    assert original["matches"][0]["champion_name"] == "old"
    assert actual["request"]["data_dragon_version"] == "16.17.1"
    row = actual["matches"][0]
    assert (row["role"], row["gold_earned"], row["game_version"]) == ("UTILITY", 5000, "16.17.100.1")
    assert row["item_purchases"] == [{"item_id": 1, "timestamp": 100, "item_name": "correct"}]


def test_bad_saved_identity_stops_before_filesystem(tmp_path):
    with pytest.raises(ValueError, match="run_invalid"):
        load_saved_summary(tmp_path, run_id="../escaped", expected_digest="a" * 64,
                           riot_id="Offline#TEST", routing_region="asia", count=5, queue=420)


@pytest.mark.parametrize("ci", [None, {"headSha": "b" * 40, "status": "completed", "conclusion": "success"}])
def test_real_provider_without_exact_public_evidence_stops_before_saved_input_or_clients(tmp_path, monkeypatch, ci):
    import app.evaluation.coach_real_data_golden_slice as module
    import app.evaluation.golden_saved_input as saved
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_assert_clean_tree", lambda: None)
    monkeypatch.setattr(module, "_implementation_sha", lambda: "a" * 40)
    def forbidden(*args, **kwargs):
        raise AssertionError("source work must follow real evidence validation")
    monkeypatch.setattr(saved, "load_saved_summary", forbidden)
    monkeypatch.setattr(module, "RiotClient", forbidden)
    with pytest.raises(ValueError, match="public_ci_mismatch"):
        run_golden_slice(config(with_provider=True), environ={}, ci=ci)
    assert not (tmp_path / "data/runs/golden_slice_reservations").exists()
