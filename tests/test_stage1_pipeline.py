import argparse
import unittest

from app.artifacts import (
    coach_report_path,
    deterministic_report_path,
    player_slug,
)
from app.lol.summary_schema import (
    SUMMARY_SCHEMA_VERSION,
    SummaryValidationError,
    validate_summary_document,
)
from scripts.build_player_summary import build_player_summary, parse_riot_id


def match_detail(match_id: str, duration: int) -> dict:
    target = {
        "puuid": "target-puuid",
        "participantId": 1,
        "teamId": 100,
        "championId": 58,
        "championName": "Renekton",
        "teamPosition": "TOP",
        "individualPosition": "TOP",
        "win": True,
        "summoner1Id": 4,
        "summoner2Id": 12,
        "perks": {"styles": []},
        "kills": 2,
        "deaths": 1,
        "assists": 3,
        "totalMinionsKilled": 50,
        "neutralMinionsKilled": 0,
        "goldEarned": 5000,
        "totalDamageDealtToChampions": 6000,
        "visionScore": 10,
        "item0": 1054,
        "item1": 0,
        "item2": 0,
        "item3": 0,
        "item4": 0,
        "item5": 0,
        "item6": 3340,
        "riotIdGameName": "Player Name",
        "riotIdTagline": "CN1",
    }
    teammate = dict(target)
    teammate.update(
        {
            "puuid": "teammate",
            "participantId": 2,
            "kills": 3,
            "deaths": 2,
            "assists": 1,
            "goldEarned": 4500,
            "totalDamageDealtToChampions": 4000,
        }
    )
    return {
        "metadata": {"matchId": match_id},
        "info": {
            "gameDuration": duration,
            "gameVersion": "16.13.1",
            "queueId": 420,
            "participants": [target, teammate],
        },
    }


class FakeClient:
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> dict:
        return {"gameName": game_name, "tagLine": tag_line, "puuid": "target-puuid"}

    def get_recent_match_ids(self, puuid: str, count: int, queue: int | None):
        return ["MATCH_NORMAL", "MATCH_SHORT"]

    def get_match_detail(self, match_id: str) -> dict:
        return match_detail(match_id, 1200 if match_id == "MATCH_NORMAL" else 180)

    def get_match_timeline(self, match_id: str) -> dict:
        if match_id == "MATCH_SHORT":
            raise RuntimeError("timeline unavailable")
        return {
            "info": {
                "frames": [
                    {
                        "participantFrames": {
                            "1": {
                                "minionsKilled": 0,
                                "jungleMinionsKilled": 0,
                                "totalGold": 500,
                                "currentGold": 500,
                                "xp": 0,
                                "level": 1,
                            }
                        },
                        "events": [],
                    }
                ]
            }
        }


class FakeDataDragon:
    version = "16.13.1"
    language = "zh_CN"

    def enrich_match_row(self, row: dict) -> dict:
        row["champion_name"] = "雷克顿"
        row["item_names"] = ["多兰之盾"]
        row["summoner_spell_names"] = ["闪现", "传送"]
        row["rune_names"] = []
        return row

    def enrich_item_purchases(self, purchases: list[dict]) -> list[dict]:
        return purchases


class StageOnePipelineTests(unittest.TestCase):
    def test_riot_id_parser_uses_last_hash(self):
        self.assertEqual(("Name#Part", "CN1"), parse_riot_id("Name#Part#CN1"))
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_riot_id("missing-tag")

    def test_artifact_paths_are_player_specific(self):
        summary = {"player": {"game_name": "Player Name", "tag_line": "CN/1"}}
        self.assertEqual("Player_Name_CN_1", player_slug("Player Name", "CN/1"))
        self.assertEqual(
            "reports/riftcoach_report_Player_Name_CN_1.md",
            deterministic_report_path(summary).as_posix(),
        )
        self.assertEqual(
            "reports/riftcoach_coach_report_Player_Name_CN_1.md",
            coach_report_path(summary).as_posix(),
        )

    def test_short_match_and_missing_timeline_are_explicit(self):
        summary = build_player_summary(
            client=FakeClient(),
            ddragon=FakeDataDragon(),
            game_name="Player Name",
            tag_line="CN1",
            count=10,
            queue=420,
            min_duration_seconds=300,
        )

        self.assertEqual(SUMMARY_SCHEMA_VERSION, summary["schema_version"])
        self.assertEqual(1, summary["recent_summary"]["games_analyzed"])
        self.assertEqual(1, len(summary["excluded_matches"]))
        short_match = summary["matches"][1]
        self.assertFalse(short_match["included_in_aggregate"])
        self.assertEqual("unavailable", short_match["timeline_status"])
        self.assertIn("timeline unavailable", short_match["timeline_error"])
        validate_summary_document(summary)

    def test_schema_rejects_unversioned_documents(self):
        with self.assertRaises(SummaryValidationError):
            validate_summary_document({"matches": []})


if __name__ == "__main__":
    unittest.main()
