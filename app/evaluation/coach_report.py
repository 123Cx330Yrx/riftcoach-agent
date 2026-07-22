import json
import re


JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def build_fact_pack(summary: dict) -> dict:
    """Keep the facts needed to verify claims made by a Coach report."""
    recent = summary.get("recent_summary", {})
    matches = []
    for row in summary.get("matches", []):
        matches.append(
            {
                "match_id": row.get("match_id"),
                "champion": row.get("champion_name"),
                "role": row.get("role"),
                "win": row.get("win"),
                "included_in_aggregate": row.get("included_in_aggregate"),
                "timeline_status": row.get("timeline_status"),
                "kills": row.get("kills"),
                "deaths": row.get("deaths"),
                "assists": row.get("assists"),
                "cs_per_min": row.get("cs_per_min"),
                "gold_per_min": row.get("gold_per_min"),
                "damage_per_min": row.get("damage_per_min"),
                "vision_score": row.get("vision_score"),
                "kill_participation": row.get("kill_participation"),
                "deaths_before_15": row.get("deaths_before_15"),
                "death_times": row.get("death_times", []),
                "items": row.get("item_names", []),
            }
        )

    return {
        "player": summary.get("player", {}),
        "request": summary.get("request", {}),
        "aggregate": {
            key: recent.get(key)
            for key in (
                "games_analyzed",
                "wins",
                "losses",
                "win_rate",
                "main_role",
                "averages",
                "win_loss_comparison",
                "champion_summary",
                "role_summary",
            )
        },
        "matches": matches,
        "excluded_matches": summary.get("excluded_matches", []),
        "failed_matches": summary.get("failed_matches", []),
    }


def build_evaluation_prompt(fact_pack: dict, report: str) -> str:
    return f"""
你是 RiftCoach 的独立质量审查员。请逐条核对 Coach 报告是否忠于结构化事实。

重点检查：
1. 英雄、位置、胜负、KDA、指标和时间是否引用正确。
2. 是否把两场同为胜局或同为输局的比赛错误写成胜负对比。
3. 是否跨英雄、跨位置比较后声称是“同位置赢局水平”。
4. 报告自行计算的派生均值或排除样本后的数值能否由输入复算。
5. 是否把相关性、共同变化或复盘假设写成因果结论。
6. 是否引用输入中不存在的版本 Meta、英雄胜率、装备胜率、录像细节或玩家意图。
7. 训练建议可以作为待验证方向，但不能伪装成已证实原因。

只输出合法 JSON，不要输出 Markdown。格式：
{{
  "score": 0到100的整数,
  "verdict": "pass" 或 "needs_revision" 或 "fail",
  "issues": [
    {{
      "severity": "high" 或 "medium" 或 "low",
      "category": "fact_error/unsupported_comparison/derived_math/causality/meta_hallucination/other",
      "quote": "报告原句",
      "evidence": "结构化数据中的直接证据",
      "explanation": "为什么有问题",
      "suggested_correction": "建议改写"
    }}
  ],
  "passed_checks": ["通过的检查项"],
  "summary": "简短总评"
}}

如果没有问题，issues 必须是空数组。不要为了显得严格而制造问题。

【结构化事实】
{json.dumps(fact_pack, ensure_ascii=False, indent=2)}

【待审查 Coach 报告】
{report}
""".strip()


def parse_evaluation_response(content: str) -> dict:
    text = content.strip()
    fenced = JSON_FENCE_PATTERN.search(text)
    if fenced:
        text = fenced.group(1).strip()
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("Evaluation response must be a JSON object.")
    if not isinstance(result.get("issues"), list):
        raise ValueError("Evaluation response is missing an issues list.")
    if result.get("verdict") not in {"pass", "needs_revision", "fail"}:
        raise ValueError("Evaluation response contains an invalid verdict.")
    score = result.get("score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Evaluation score must be an integer from 0 to 100.")
    return result


def build_revision_prompt(report: str, evaluation: dict) -> str:
    """Ask for a minimal revision limited to reported factual issues."""
    issues = evaluation.get("issues", [])
    return f"""
请修订下面的 RiftCoach Coach 报告。

严格要求：
1. 只修正评测 issues 明确指出的句子和被这些修正直接影响的上下文。
2. 保留原有 Markdown 标题、章节顺序、语气和其他已通过内容。
3. 不新增比赛事实、版本 Meta、录像细节或新的推断。
4. 每个问题必须按照 evidence 和 suggested_correction 修正。
5. 不要在正文中谈论“评测器”或“修订过程”。
6. 直接输出完整修订版 Markdown，不要使用代码块。

【评测问题】
{json.dumps(issues, ensure_ascii=False, indent=2)}

【原报告】
{report}
""".strip()


def validate_revised_report(report: str, original_report: str) -> None:
    required_headings = [
        "# RiftCoach 教练式复盘报告",
        "## 1. 总体结论",
        "## 2. 当前表现亮点",
        "## 3. 主要风险点",
        "## 4. 赢局与输局差异",
        "## 5. 下一步复盘建议",
        "## 6. 训练计划",
        "## 7. 数据边界与知识来源",
    ]
    missing = [heading for heading in required_headings if heading not in report]
    if missing:
        raise ValueError(f"Revised report is missing headings: {missing}")
    if len(report) < len(original_report) * 0.7:
        raise ValueError("Revised report is unexpectedly shorter than the original.")
