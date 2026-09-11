from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from app.evidence.adapters import EvidenceAdapterError
from app.evidence.summary_bridge import summary_to_evidence
from tests.test_evidence_fusion_vertical import NOW, _meta, _patch, _static, _summary_row


def summary(games=2):
    return {
        "schema_version": "1.0",
        "metadata": {"generated_at_utc": NOW.isoformat(), "source": "synthetic_fixture",
                     "matches_requested": 5, "matches_received": games, "matches_analyzed": games},
        "player": {"game_name": "Demo", "tag_line": "TEST", "riot_id": "Demo#TEST"},
        "request": {"count": 5, "queue": 420, "requested_queue": 420,
                    "queue_fallback_used": False, "data_dragon_version": "15.16.1",
                    "data_dragon_language": "zh_CN"},
        "recent_summary": {"games_analyzed": games},
        "matches": [{**_summary_row(), "match_id": f"ASIA1_{i}", "included_in_aggregate": True}
                    for i in range(games)],
        "excluded_matches": [], "failed_matches": [],
    }


def convert(value, **kwargs):
    return summary_to_evidence(value, routing_region="asia", now=NOW, **kwargs)


@pytest.mark.parametrize("games", [2, 5])
def test_same_source_immutable_projection_and_digest(games):
    value = summary(games)
    original = copy.deepcopy(value)
    result = convert(value)
    assert (result.included_count, result.excluded_count, result.failed_count) == (games, 0, 0)
    assert result.digest_scope == "summary_projection"
    assert result.observation_basis == "summary_generated_at"
    assert result.bundle.has_valid_digest()
    assert len(result.bundle.riot_matches) == games
    assert result.bundle.data_dragon is None
    assert result.bundle.gaps
    assert value == original
    assert convert(dict(reversed(list(value.items())))).summary_digest == result.summary_digest
    value["matches"][0]["win"] = False
    assert convert(value).summary_digest != result.summary_digest
    assert result.bundle.riot_matches[0].win is True
    with pytest.raises(FrozenInstanceError):
        result.included_count = 10
    assert "must-not-enter-evidence" not in str(result)


def test_excluded_failed_timeline_and_queue_fallback_are_not_invented():
    value = summary()
    value["matches"][0].update(game_version="16.16.804.9184", timeline_status="unavailable", queue_id=400)
    value["matches"][1]["included_in_aggregate"] = False
    value["excluded_matches"] = [{"match_id": "ASIA1_1", "reason": "short_game"}]
    value["failed_matches"] = [{"match_id": "ASIA1_2", "error": "private-error"}]
    value["metadata"].update(matches_received=3, matches_analyzed=1)
    value["recent_summary"]["games_analyzed"] = 1
    value["request"].update(queue=None, queue_fallback_used=True)
    result = convert(value)
    assert (result.included_count, result.excluded_count, result.failed_count) == (1, 1, 1)
    assert result.requested_queue == 420 and result.effective_queue is None
    assert result.queue_fallback_used is True
    fact = result.bundle.riot_matches[0]
    assert fact.queue_id == 400 and fact.patch_version == "16.16"
    assert not fact.timeline_available
    assert "private-error" not in str(result)


@pytest.mark.parametrize("kind", ["partial", "expired", "conflict"])
def test_reuses_existing_meta_rules(kind):
    meta = _meta(patch="15.17" if kind == "conflict" else None)
    result = summary_to_evidence(summary(), routing_region="asia",
        now=NOW + timedelta(hours=1) if kind == "expired" else NOW,
        data_dragon=_static(), official_patch=_patch(), meta_evidence=(meta,))
    if kind == "partial":
        assert result.bundle.disposition.value == "complete"
        assert result.bundle.joins[0].status.value == "joined_partial"
    else:
        assert result.bundle.disposition.value == "degraded"
    assert "exact_patch_meta_comparison" not in result.bundle.claims


def test_mixed_versions_and_explicit_observation():
    value = summary()
    value["matches"][1]["game_version"] = "16.16.804.9184"
    result = convert(value, observed_at=NOW - timedelta(minutes=1), data_dragon=_static())
    assert [r.patch_version for r in result.bundle.riot_matches] == ["15.16", "16.16"]
    assert result.observation_basis == "caller_observed_at"
    assert result.bundle.riot_matches[0].observed_at == NOW - timedelta(minutes=1)
    assert result.bundle.conflicts


@pytest.mark.parametrize("case", [
    "container", "metadata", "row", "duplicate", "failed_duplicate", "counts", "bool_count",
    "flag", "empty", "excluded_mismatch", "missing_time", "naive_time", "future_time",
    "static_identity", "queue", "fallback", "region", "timeline", "schema", "non_json",
])
def test_invalid_summary_fails_with_body_free_code(case):
    value = summary()
    if case == "container": value = []
    elif case == "metadata": value["metadata"] = []
    elif case == "row": value["matches"][0] = "private-value"
    elif case == "duplicate": value["matches"][1]["match_id"] = "ASIA1_0"
    elif case == "failed_duplicate": value["failed_matches"] = [{"match_id": "ASIA1_0"}]
    elif case == "counts": value["metadata"]["matches_analyzed"] = 5
    elif case == "bool_count": value["metadata"]["matches_analyzed"] = True
    elif case == "flag": value["matches"][0]["included_in_aggregate"] = 1
    elif case == "empty": value = summary(0)
    elif case == "excluded_mismatch": value["excluded_matches"] = [{"match_id": "ASIA1_0"}]
    elif case == "missing_time": del value["metadata"]["generated_at_utc"]
    elif case == "naive_time": value["metadata"]["generated_at_utc"] = "2026-08-23T08:00:00"
    elif case == "future_time": value["metadata"]["generated_at_utc"] = (NOW + timedelta(days=1)).isoformat()
    elif case == "static_identity": value["request"]["data_dragon_version"] = "15.17.1"
    elif case == "queue": value["matches"][0]["queue_id"] = 400
    elif case == "fallback": value["request"]["queue_fallback_used"] = True
    elif case == "region": value["request"]["region"] = "europe"
    elif case == "timeline": value["matches"][0]["timeline_status"] = "invented"
    elif case == "schema": value["schema_version"] = "private-value"
    elif case == "non_json": value["private"] = float("nan")
    with pytest.raises(EvidenceAdapterError, match="^[a-z_]+$") as error:
        convert(value, data_dragon=_static())
    assert "private" not in str(error.value)


def test_conversion_no_io(monkeypatch):
    import builtins
    import io
    import os
    import socket
    import importlib
    import app.evidence.summary_bridge as bridge

    value = summary()
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O forbidden")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(io, "open", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    # Reload only this module; Python's import loader necessarily reads source.
    importlib.reload(bridge)
    assert convert(value).included_count == 2


@pytest.mark.parametrize("kwargs", [
    {"routing_region": "https://private.invalid"}, {"now": NOW.replace(tzinfo=None)},
    {"observed_at": NOW + timedelta(days=1)}, {"data_dragon": {}},
    {"official_patch": {}}, {"meta_evidence": ({},)},
])
def test_invalid_explicit_boundary_inputs(kwargs):
    args = {"routing_region": "asia", "now": NOW, **kwargs}
    with pytest.raises(EvidenceAdapterError, match="^summary_evidence_invalid$"):
        summary_to_evidence(summary(), **args)


def test_source_from_future_rejected():
    from app.evidence.fusion import DataDragonSnapshot
    source = DataDragonSnapshot(version="15.16.1", language="zh_CN", catalog_digest="d" * 64,
                                retrieved_at=NOW + timedelta(seconds=1))
    with pytest.raises(EvidenceAdapterError, match="^summary_evidence_invalid$"):
        convert(summary(), data_dragon=source)
