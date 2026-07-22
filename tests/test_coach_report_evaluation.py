import unittest

from app.evaluation.coach_report import (
    build_fact_pack,
    build_revision_prompt,
    parse_evaluation_response,
    validate_revised_report,
)


class CoachReportEvaluationTests(unittest.TestCase):
    def test_fact_pack_keeps_win_role_and_metrics(self):
        summary = {
            "player": {"riot_id": "A#B"},
            "request": {"count": 1},
            "recent_summary": {"games_analyzed": 1, "wins": 0, "losses": 1},
            "matches": [
                {
                    "match_id": "KR_1",
                    "champion_name": "鳄鱼",
                    "role": "上路",
                    "win": False,
                    "kills": 1,
                    "deaths": 1,
                    "assists": 1,
                    "damage_per_min": 498,
                }
            ],
        }
        facts = build_fact_pack(summary)
        self.assertFalse(facts["matches"][0]["win"])
        self.assertEqual("上路", facts["matches"][0]["role"])
        self.assertEqual(498, facts["matches"][0]["damage_per_min"])

    def test_parses_valid_evaluation(self):
        content = """```json
        {"score": 85, "verdict": "needs_revision", "issues": [], "passed_checks": [], "summary": "ok"}
        ```"""
        result = parse_evaluation_response(content)
        self.assertEqual(85, result["score"])

    def test_rejects_invalid_score(self):
        with self.assertRaises(ValueError):
            parse_evaluation_response(
                '{"score": 101, "verdict": "pass", "issues": []}'
            )

    def test_revision_prompt_contains_only_structured_issues_and_report(self):
        prompt = build_revision_prompt(
            "# RiftCoach 教练式复盘报告\n原文",
            {"issues": [{"quote": "错误句", "suggested_correction": "正确句"}]},
        )
        self.assertIn("错误句", prompt)
        self.assertIn("正确句", prompt)
        self.assertIn("只修正", prompt)

    def test_revised_report_requires_all_headings(self):
        with self.assertRaises(ValueError):
            validate_revised_report("# RiftCoach 教练式复盘报告", "原报告正文" * 20)


if __name__ == "__main__":
    unittest.main()
