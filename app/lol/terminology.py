import json
from copy import deepcopy
from pathlib import Path


ROLE_DISPLAY_NAMES = {
    "TOP": "上路",
    "JUNGLE": "打野",
    "MIDDLE": "中路",
    "BOTTOM": "下路",
    "UTILITY": "辅助",
    "SUPPORT": "辅助",
    "NONE": "未知位置",
    "": "未知位置",
}


def display_role(role: str | None) -> str:
    if role is None:
        return "未知位置"
    return ROLE_DISPLAY_NAMES.get(role.upper(), role)


class TerminologyStore:
    """Persistent, reviewed CN-community terminology keyed by Riot IDs."""

    def __init__(self, path: Path):
        self.path = path
        if not path.exists():
            raise FileNotFoundError(f"Terminology file not found: {path}")
        self.data = json.loads(path.read_text(encoding="utf-8"))

    def get_item(self, item_id: int | str | None) -> dict | None:
        if item_id is None:
            return None
        return self.data.get("items", {}).get(str(item_id))

    def get_champion(self, champion_id: int | str | None) -> dict | None:
        if champion_id is None:
            return None
        return self.data.get("champions", {}).get(str(champion_id))

    def preferred_item_name(self, item_id: int | str | None, fallback: str) -> str:
        term = self.get_item(item_id)
        if term and term.get("status") == "confirmed":
            return term.get("preferred_name") or fallback
        return fallback

    def preferred_champion_name(
        self,
        champion_id: int | str | None,
        fallback: str,
    ) -> str:
        term = self.get_champion(champion_id)
        if term and term.get("status") == "confirmed":
            return term.get("preferred_name") or fallback
        return fallback

    def apply_to_summary(self, summary: dict, ddragon) -> dict:
        """Return a display copy using confirmed terms and official fallbacks."""
        result = deepcopy(summary)
        champion_names = {}

        for row in result.get("matches", []):
            row["role_code"] = row.get("role")
            row["role"] = display_role(row.get("role"))
            champion_id = row.get("champion_id")
            official_champion = ddragon.get_champion_official_name(
                champion_id,
                fallback=row.get("champion_name_en", ""),
            )
            display_champion = self.preferred_champion_name(
                champion_id,
                official_champion,
            )
            champion_names[official_champion] = display_champion
            champion_names[row.get("champion_name", "")] = display_champion
            row["champion_official_name"] = official_champion
            row["champion_display_name"] = display_champion
            row["champion_name"] = display_champion

            final_items = []
            display_item_names = []
            for item_id in row.get("items", []):
                if not item_id:
                    continue
                official_item = ddragon.get_item_name(item_id)
                display_item = self.preferred_item_name(item_id, official_item)
                final_items.append(
                    {
                        "item_id": item_id,
                        "official_name": official_item,
                        "display_name": display_item,
                    }
                )
                display_item_names.append(display_item)
            row["final_items"] = final_items
            row["item_display_names"] = display_item_names
            row["item_names"] = display_item_names

            for purchase in row.get("item_purchases", []):
                item_id = purchase.get("item_id")
                official_item = ddragon.get_item_name(item_id)
                purchase["item_official_name"] = official_item
                purchase["item_display_name"] = self.preferred_item_name(
                    item_id,
                    official_item,
                )
                purchase["item_name"] = purchase["item_display_name"]

        recent = result.get("recent_summary", {})
        recent["main_role_code"] = recent.get("main_role")
        recent["main_role"] = display_role(recent.get("main_role"))
        recent["main_champions"] = [
            champion_names.get(name, name)
            for name in recent.get("main_champions", [])
        ]
        for row in recent.get("champion_summary", []):
            row["champion"] = champion_names.get(row.get("champion"), row.get("champion"))
        for row in recent.get("role_summary", []):
            row["role_code"] = row.get("role")
            row["role"] = display_role(row.get("role"))
        return result
