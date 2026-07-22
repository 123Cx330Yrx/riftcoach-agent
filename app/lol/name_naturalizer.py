import json
import re
from typing import Any


JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def collect_name_candidates(summary: dict, ddragon: Any, terminology: Any = None) -> dict:
    """Collect unique official names without deciding community aliases."""
    champions = {}
    items = {}
    confirmed_champions = []
    confirmed_items = []

    for row in summary.get("matches", []):
        champion_id = row.get("champion_id")
        if champion_id is not None:
            champion_id = int(champion_id)
            candidate = {
                "champion_id": champion_id,
                "english_name": row.get("champion_name_en", ""),
                "official_name": ddragon.get_champion_official_name(
                    champion_id,
                    fallback=row.get("champion_name_en", ""),
                ),
                "official_title": ddragon.get_champion_title(champion_id),
            }
            term = terminology.get_champion(champion_id) if terminology else None
            if term and term.get("status") == "confirmed":
                confirmed_champions.append({**candidate, **term})
                champions.pop(champion_id, None)
            else:
                champions[champion_id] = candidate

        for item_id in row.get("items", []):
            if not item_id:
                continue
            name = ddragon.get_item_name(item_id)
            candidate = {"item_id": int(item_id), "official_name": name}
            term = terminology.get_item(item_id) if terminology else None
            if term and term.get("status") == "confirmed":
                confirmed_items.append({**candidate, **term})
                items.pop(int(item_id), None)
            else:
                items[int(item_id)] = candidate

    return {
        "champions": sorted(champions.values(), key=lambda item: item["champion_id"]),
        "items": sorted(items.values(), key=lambda item: item["item_id"]),
        "confirmed_champions": _deduplicate_by_id(confirmed_champions, "champion_id"),
        "confirmed_items": _deduplicate_by_id(confirmed_items, "item_id"),
    }


def _deduplicate_by_id(rows: list[dict], key: str) -> list[dict]:
    unique = {int(row[key]): row for row in rows}
    return [unique[item_id] for item_id in sorted(unique)]


def build_naturalization_prompt(candidates: dict) -> str:
    return f"""
你熟悉英雄联盟国服玩家的日常用语。请为下面出现的英雄和装备选择最自然、最普遍的国服称呼。

这不是机械翻译任务，也不是要求全部改成外号。请自行判断：
- 如果国服玩家普遍使用外号或简称，就使用那个称呼。
- 如果玩家通常直接使用英雄本名或装备短名，就保留本名或短名。
- 不要使用“九尾妖狐”“荒漠屠夫”这类称号式全称作为日常称呼。
- 不要创造冷门、地区性或没有广泛共识的外号。
- 每个结果给一句简短理由，说明它属于常用外号、常用简称或通常直接叫本名。

只输出合法 JSON，不要输出 Markdown 代码块。结构必须是：
{{
  "champions": [
    {{"champion_id": 1, "official_name": "官方本名", "natural_name": "自然称呼", "reason": "简短理由"}}
  ],
  "items": [
    {{"item_id": 1001, "official_name": "官方名称", "natural_name": "自然称呼", "reason": "简短理由"}}
  ]
}}

待判断数据：
{json.dumps(candidates, ensure_ascii=False, indent=2)}
""".strip()


def parse_naturalization_response(content: str) -> dict:
    """Parse plain JSON or JSON wrapped in a Markdown fence."""
    text = content.strip()
    fenced = JSON_FENCE_PATTERN.search(text)
    if fenced:
        text = fenced.group(1).strip()

    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("Naturalization response must be a JSON object.")
    if not isinstance(result.get("champions"), list):
        raise ValueError("Naturalization response is missing a champions list.")
    if not isinstance(result.get("items"), list):
        raise ValueError("Naturalization response is missing an items list.")
    return result
