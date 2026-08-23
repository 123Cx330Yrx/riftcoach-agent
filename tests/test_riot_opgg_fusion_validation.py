from __future__ import annotations

import json
from pathlib import Path

from scripts.run_riot_opgg_fusion_validation import _typed_riot_match


def test_typed_riot_projection_uses_digest_identity_and_allowlisted_facts() -> None:
    result = {
        "relationship_role": "observed",
        "routing_region": "asia",
        "observed_at": "2026-08-23T02:21:21.760385+00:00",
        "matches": {
            "selected_match_id_digest": "0" * 64,
        },
        "match": {
            "game_version": "16.16.804.9184",
            "queue_id": 420,
            "game_duration_seconds": 1925,
            "target": {
                "champion_id": 84,
                "champion": "Akali",
                "role": "MIDDLE",
                "win": True,
            },
        },
    }
    evidence = _typed_riot_match(result)
    assert evidence.match_id == f"digest:{'0' * 32}"
    assert evidence.patch_version == "16.16"
    assert evidence.position == "mid"
    assert evidence.champion_id == 84
    assert "puuid" not in repr(evidence).casefold()


def test_live_mid_schema_diagnostic_is_body_free_and_distinct_from_fixture() -> None:
    result = json.loads(
        Path(
            "data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v2.json"
        ).read_text(encoding="utf-8")
    )
    fixture = json.loads(
        Path(
            "data/evaluation/results/mcp/opgg_mid_schema_drift_fixture_v1.json"
        ).read_text(encoding="utf-8")
    )

    diagnostic = result["opgg"]["schema_diagnostic"]
    controlled = fixture["failure"]["diagnostic"]
    assert result["result"] == "failed"
    assert result["body_free"] is True
    assert fixture["lifecycle_status"] == "retained_pre_fix_evidence"
    assert result["external_io"] == {
        "key_reads": 0,
        "llm_provider_calls": 0,
        "opgg_tools_call_calls": 1,
        "riot_calls": 0,
    }
    assert {
        name: diagnostic[name]
        for name in (
            "stage",
            "position",
            "row_name",
            "field_name",
            "field_index",
            "observed_node_type",
        )
    } == {
        name: controlled[name]
        for name in (
            "stage",
            "position",
            "row_name",
            "field_name",
            "field_index",
            "observed_node_type",
        )
    }
    assert diagnostic["text_digest"] != controlled["text_digest"]
    assert diagnostic["text_length"] != controlled["text_length"]
    assert "DK ShowMaker" not in json.dumps(result)


def test_post_fix_live_replay_creates_body_free_two_source_bundle() -> None:
    result = json.loads(
        Path(
            "data/evaluation/results/riot_opgg_fusion_validation_2026-08-23-v3.json"
        ).read_text(encoding="utf-8")
    )

    assert result["result"] == "passed"
    assert result["body_free"] is True
    assert result["external_io"] == {
        "key_reads": 0,
        "llm_provider_calls": 0,
        "opgg_tools_call_calls": 1,
        "riot_calls": 0,
    }
    assert result["opgg"]["fact_count"] == 10
    assert result["opgg"]["position"] == "mid"
    assert result["bundle"]["bundle_digest"] == (
        "69ed8a83140da73818ed46a7857947d780d0132a309a6317036438161fbfff1a"
    )
    assert result["bundle"]["sources"]["riot_official"]["match_count"] == 1
    assert result["bundle"]["sources"]["opgg"]["evidence_count"] == 1
    assert result["bundle"]["disposition"] == "degraded"
    assert result["bundle"]["joins"][0]["status"] == "unjoined"
    assert "meta_join_missing" in {
        gap["code"] for gap in result["bundle"]["gaps"]
    }
    assert "DK ShowMaker" not in json.dumps(result)
