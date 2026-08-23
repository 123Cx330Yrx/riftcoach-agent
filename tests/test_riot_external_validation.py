from __future__ import annotations

from typing import Any

import pytest

from scripts.run_riot_external_validation import parse_riot_id, run_validation


class FakeRiotClient:
    def __init__(self, *, region: str) -> None:
        self.region = region

    def get_account_by_riot_id(self, game_name: str, tag_line: str, *, timeout_s: float) -> dict[str, str]:
        assert (game_name, tag_line, timeout_s) == ("DK ShowMaker", "KR1", 15)
        return {"puuid": "private-puuid", "gameName": "DK ShowMaker", "tagLine": "KR1"}

    def get_recent_match_ids(self, puuid: str, *, count: int, queue: int | None, timeout_s: float) -> list[str]:
        assert (puuid, count, queue, timeout_s) == ("private-puuid", 1, 420, 15)
        return ["KR_123"]

    def get_match_detail(self, match_id: str, *, timeout_s: float) -> dict[str, Any]:
        assert (match_id, timeout_s) == ("KR_123", 15)
        return {
            "info": {
                "gameVersion": "15.16.1",
                "queueId": 420,
                "gameDuration": 1800,
                "participants": [
                    {
                        "puuid": "private-puuid",
                        "championName": "Syndra",
                        "teamPosition": "MIDDLE",
                        "win": True,
                        "kills": 7,
                        "deaths": 2,
                        "assists": 8,
                    }
                ],
            }
        }


def test_parse_riot_id_requires_bounded_game_name_and_tag() -> None:
    assert parse_riot_id(" DK ShowMaker#KR1 ") == (
        "DK ShowMaker",
        "KR1",
        "DK ShowMaker#KR1",
    )
    with pytest.raises(ValueError):
        parse_riot_id("ShowMaker")


def test_fake_validation_is_body_free_and_does_not_persist_private_ids() -> None:
    result = run_validation(
        riot_id="DK ShowMaker#KR1",
        region="asia",
        relationship_role="observed",
        client_factory=FakeRiotClient,
    )
    assert result["result"] == "passed"
    assert result["body_free"] is True
    assert result["identity"]["puuid_digest"] != "private-puuid"
    assert result["matches"]["selected_match_id_digest"] != "KR_123"
    assert "private-puuid" not in str(result)
    assert "KR_123" not in str(result)
    assert result["external_io"]["key_reads"] == 1
