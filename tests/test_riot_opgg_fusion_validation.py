from __future__ import annotations

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
