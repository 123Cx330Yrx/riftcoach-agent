import json
import tempfile
import unittest
from pathlib import Path

from app.lol.terminology import TerminologyStore


class FakeDataDragon:
    def get_champion_official_name(self, champion_id, fallback=""):
        return {58: "雷克顿"}.get(champion_id, fallback)

    def get_item_name(self, item_id):
        return {3047: "铁板靴", 6692: "星蚀"}[item_id]


class TerminologyDisplayTests(unittest.TestCase):
    def test_confirmed_names_override_and_unknown_names_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terms.json"
            path.write_text(
                json.dumps(
                    {
                        "champions": {
                            "58": {
                                "preferred_name": "鳄鱼",
                                "status": "confirmed",
                            }
                        },
                        "items": {
                            "3047": {
                                "preferred_name": "布甲鞋",
                                "status": "confirmed",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            summary = {
                "matches": [
                    {
                        "champion_id": 58,
                        "champion_name": "雷克顿",
                        "role": "TOP",
                        "items": [3047, 6692, 0],
                        "item_purchases": [],
                    }
                ],
                "recent_summary": {
                    "main_role": "TOP",
                    "main_champions": ["雷克顿"],
                    "champion_summary": [{"champion": "雷克顿"}],
                    "role_summary": [{"role": "TOP", "games": 1}],
                },
            }
            result = TerminologyStore(path).apply_to_summary(summary, FakeDataDragon())
            match = result["matches"][0]
            self.assertEqual("鳄鱼", match["champion_name"])
            self.assertEqual(["布甲鞋", "星蚀"], match["item_names"])
            self.assertEqual("上路", match["role"])
            self.assertEqual("TOP", match["role_code"])
            self.assertEqual("鳄鱼", result["recent_summary"]["main_champions"][0])
            self.assertEqual("上路", result["recent_summary"]["main_role"])
            self.assertEqual("上路", result["recent_summary"]["role_summary"][0]["role"])
            self.assertEqual("雷克顿", summary["matches"][0]["champion_name"])


if __name__ == "__main__":
    unittest.main()
