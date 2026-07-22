import unittest

from app.lol.terminology_review import (
    apply_confirmed_reviews,
    apply_review_decisions,
    build_review_queue,
)


class FakeDataDragon:
    def get_champion_official_name(self, champion_id):
        return {58: "雷克顿"}[champion_id]

    def get_item_name(self, item_id):
        return {3157: "中娅沙漏"}[item_id]


class TerminologyReviewTests(unittest.TestCase):
    def test_queue_resolves_missing_item_id(self):
        experiment = {
            "champions": [],
            "items": [
                {
                    "official_name": "中娅沙漏",
                    "natural_name": "中娅",
                    "reason": "常用简称",
                }
            ],
        }
        summary = {"matches": [{"champion_id": 58, "items": [3157]}]}
        queue = build_review_queue(experiment, summary, FakeDataDragon())
        self.assertEqual(3157, queue["entries"][0]["riot_id"])
        self.assertEqual("pending", queue["entries"][0]["status"])

    def test_only_confirmed_entries_are_applied(self):
        review = {
            "entries": [
                {
                    "entity_type": "item",
                    "riot_id": 3157,
                    "official_name": "中娅沙漏",
                    "approved_name": "中娅",
                    "status": "confirmed",
                },
                {
                    "entity_type": "champion",
                    "riot_id": 58,
                    "official_name": "雷克顿",
                    "approved_name": "鳄鱼",
                    "status": "pending",
                },
            ]
        }
        updated, applied = apply_confirmed_reviews(
            review,
            {"schema_version": 1, "items": {}, "champions": {}},
        )
        self.assertEqual(1, applied)
        self.assertEqual("中娅", updated["items"]["3157"]["preferred_name"])
        self.assertNotIn("58", updated["champions"])

    def test_decisions_confirm_only_listed_ids(self):
        review = {
            "entries": [
                {
                    "entity_type": "item",
                    "riot_id": 3047,
                    "approved_name": "护甲鞋",
                    "status": "pending",
                },
                {
                    "entity_type": "item",
                    "riot_id": 3175,
                    "approved_name": "灵能使之靴",
                    "status": "pending",
                },
            ]
        }
        updated, changed = apply_review_decisions(
            review,
            {"items": {"3047": "布甲鞋"}, "champions": {}},
        )
        self.assertEqual(1, changed)
        self.assertEqual("布甲鞋", updated["entries"][0]["approved_name"])
        self.assertEqual("confirmed", updated["entries"][0]["status"])
        self.assertEqual("pending", updated["entries"][1]["status"])


if __name__ == "__main__":
    unittest.main()
