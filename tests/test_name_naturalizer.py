import json
import tempfile
import unittest
from pathlib import Path

from app.lol.name_naturalizer import (
    collect_name_candidates,
    parse_naturalization_response,
)
from app.lol.terminology import TerminologyStore


class FakeDataDragon:
    def get_champion_official_name(self, champion_id, fallback=""):
        return {58: "雷克顿"}.get(champion_id, fallback)

    def get_champion_title(self, champion_id, fallback=""):
        return {58: "荒漠屠夫"}.get(champion_id, fallback)

    def get_item_name(self, item_id):
        return {3047: "铁板靴", 6692: "星蚀", 3157: "中娅沙漏"}[item_id]


class NameNaturalizerTests(unittest.TestCase):
    def test_collects_unique_candidates(self):
        summary = {
            "matches": [
                {
                    "champion_id": 58,
                    "champion_name_en": "Renekton",
                    "items": [3047, 6692],
                },
                {
                    "champion_id": 58,
                    "champion_name_en": "Renekton",
                    "items": [6692],
                },
            ]
        }
        result = collect_name_candidates(summary, FakeDataDragon())
        self.assertEqual(1, len(result["champions"]))
        self.assertEqual("雷克顿", result["champions"][0]["official_name"])
        self.assertEqual([3047, 6692], [item["item_id"] for item in result["items"]])

    def test_parses_fenced_json(self):
        content = '```json\n{"champions": [], "items": []}\n```'
        result = parse_naturalization_response(content)
        self.assertEqual([], result["champions"])

    def test_confirmed_terms_are_not_sent_as_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terms.json"
            path.write_text(
                json.dumps(
                    {
                        "items": {
                            "3047": {
                                "preferred_name": "布甲鞋",
                                "status": "confirmed",
                            }
                        },
                        "champions": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            terminology = TerminologyStore(path)
            summary = {
                "matches": [
                    {
                        "champion_id": 58,
                        "champion_name_en": "Renekton",
                        "items": [3047, 6692],
                    }
                ]
            }
            result = collect_name_candidates(summary, FakeDataDragon(), terminology)
            self.assertEqual([6692], [item["item_id"] for item in result["items"]])
            self.assertEqual("布甲鞋", result["confirmed_items"][0]["preferred_name"])


if __name__ == "__main__":
    unittest.main()
