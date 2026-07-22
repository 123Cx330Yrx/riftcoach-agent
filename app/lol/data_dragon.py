import json
from pathlib import Path

import requests


class DataDragonService:
    """
    Data Dragon 静态数据服务。

    作用：
    1. 获取当前 Data Dragon 最新版本号。
    2. 缓存 champion / item / summoner spell / rune 数据。
    3. 把 Riot API 里的 championId、itemId、spellId、runeId 映射成中文名。

    注意：
    - 这里不维护国服玩家外号表。
    - 官方中文名由 Data Dragon 提供。
    - 最终 Coach 报告中的“鳄鱼 / 狐狸 / 发条 / VN / 装备简称”等自然表达交给 GLM 生成。
    """

    def __init__(
        self,
        language: str = "zh_CN",
        cache_dir: str = "data/static/ddragon",
    ):
        self.language = language
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.version = self._load_latest_version()

        self.champions = self._load_champions()
        self.items = self._load_items()
        self.summoner_spells = self._load_summoner_spells()
        self.runes = self._load_runes()

        self.champion_by_id = self._build_champion_by_id()
        self.spell_by_id = self._build_spell_by_id()
        self.rune_by_id = self._build_rune_by_id()

    def _get_json(self, url: str, cache_file: Path) -> dict | list:
        if cache_file.exists():
            with cache_file.open("r", encoding="utf-8") as f:
                return json.load(f)

        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data

    def _load_latest_version(self) -> str:
        cache_file = self.cache_dir / "versions.json"
        url = "https://ddragon.leagueoflegends.com/api/versions.json"

        versions = self._get_json(url, cache_file)

        if not versions:
            raise RuntimeError("Failed to load Data Dragon versions.")

        return versions[0]

    def _load_champions(self) -> dict:
        cache_file = self.cache_dir / f"champion_{self.language}_{self.version}.json"
        url = (
            f"https://ddragon.leagueoflegends.com/cdn/{self.version}"
            f"/data/{self.language}/champion.json"
        )
        return self._get_json(url, cache_file)

    def _load_items(self) -> dict:
        cache_file = self.cache_dir / f"item_{self.language}_{self.version}.json"
        url = (
            f"https://ddragon.leagueoflegends.com/cdn/{self.version}"
            f"/data/{self.language}/item.json"
        )
        return self._get_json(url, cache_file)

    def _load_summoner_spells(self) -> dict:
        cache_file = self.cache_dir / f"summoner_{self.language}_{self.version}.json"
        url = (
            f"https://ddragon.leagueoflegends.com/cdn/{self.version}"
            f"/data/{self.language}/summoner.json"
        )
        return self._get_json(url, cache_file)

    def _load_runes(self) -> list:
        cache_file = self.cache_dir / f"runesReforged_{self.language}_{self.version}.json"
        url = (
            f"https://ddragon.leagueoflegends.com/cdn/{self.version}"
            f"/data/{self.language}/runesReforged.json"
        )
        return self._get_json(url, cache_file)

    def _build_champion_by_id(self) -> dict[int, dict]:
        result = {}

        for champion in self.champions.get("data", {}).values():
            champion_id = int(champion["key"])
            result[champion_id] = champion

        return result

    def _build_spell_by_id(self) -> dict[int, dict]:
        result = {}

        for spell in self.summoner_spells.get("data", {}).values():
            spell_id = int(spell["key"])
            result[spell_id] = spell

        return result

    def _build_rune_by_id(self) -> dict[int, dict]:
        result = {}

        for style in self.runes:
            # 主系 / 副系本身也有 id，比如精密、主宰
            if "id" in style:
                result[int(style["id"])] = {
                    "id": style["id"],
                    "name": style.get("name", ""),
                    "icon": style.get("icon", ""),
                    "type": "style",
                }

            for slot in style.get("slots", []):
                for rune in slot.get("runes", []):
                    result[int(rune["id"])] = {
                        "id": rune["id"],
                        "name": rune.get("name", ""),
                        "icon": rune.get("icon", ""),
                        "shortDesc": rune.get("shortDesc", ""),
                        "longDesc": rune.get("longDesc", ""),
                        "type": "rune",
                    }

        return result

    def get_champion_official_name(self, champion_id: int, fallback: str = "") -> str:
        """Return the localized champion name, such as 阿狸 or 雷克顿."""
        champion = self.champion_by_id.get(int(champion_id))
        if not champion:
            return fallback
        # The zh_CN payload places the personal name in `title` and the
        # epithet (九尾妖狐 / 荒漠屠夫) in `name`.
        if self.language == "zh_CN":
            return champion.get("title") or fallback
        return champion.get("name") or fallback

    def get_champion_title(self, champion_id: int, fallback: str = "") -> str:
        """Return the localized epithet, such as 九尾妖狐 or 荒漠屠夫."""
        champion = self.champion_by_id.get(int(champion_id))
        if not champion:
            return fallback
        if self.language == "zh_CN":
            return champion.get("name") or fallback
        return champion.get("title") or fallback

    def get_item_name(self, item_id: int | None) -> str:
        if not item_id:
            return ""

        item = self.items.get("data", {}).get(str(item_id))
        if not item:
            return f"未知装备({item_id})"

        return item.get("name", f"未知装备({item_id})")

    def get_summoner_spell_name(self, spell_id: int | None) -> str:
        if not spell_id:
            return ""

        spell = self.spell_by_id.get(int(spell_id))
        if not spell:
            return f"未知召唤师技能({spell_id})"

        return spell.get("name", f"未知召唤师技能({spell_id})")

    def get_rune_name(self, rune_id: int | None) -> str:
        if not rune_id:
            return ""

        rune = self.rune_by_id.get(int(rune_id))
        if not rune:
            return f"未知符文({rune_id})"

        return rune.get("name", f"未知符文({rune_id})")

    def extract_perk_ids(self, perks: dict) -> list[int]:
        """
        从 match detail 的 target["perks"] 中抽取 rune / style id。
        先只做轻量抽取，后续可以做完整符文页展示。
        """
        result = []

        for style in perks.get("styles", []):
            if "style" in style:
                result.append(style["style"])

            for selection in style.get("selections", []):
                if "perk" in selection:
                    result.append(selection["perk"])

        return result

    def enrich_match_row(self, row: dict) -> dict:
        """
        给 MatchAnalyzer 产出的单局 row 补充中文静态数据。
        """
        champion_id = row.get("champion_id")
        champion_en = row.get("champion_name_en") or row.get("champion_name") or ""

        row["champion_official_name"] = self.get_champion_official_name(
            champion_id=champion_id,
            fallback=champion_en,
        )

        row["champion_title"] = self.get_champion_title(
            champion_id=champion_id,
            fallback="",
        )

        # 数据层先统一用官方中文名，不在程序里硬写外号。
        row["champion_name"] = row["champion_official_name"]

        row["item_names"] = [
            self.get_item_name(item_id)
            for item_id in row.get("items", [])
            if item_id
        ]

        row["summoner_spell_names"] = [
            self.get_summoner_spell_name(spell_id)
            for spell_id in row.get("summoner_spell_ids", [])
            if spell_id
        ]

        row["rune_names"] = [
            self.get_rune_name(rune_id)
            for rune_id in row.get("perk_ids", [])
            if rune_id
        ]

        return row

    def enrich_item_purchases(self, item_purchases: list[dict]) -> list[dict]:
        for item in item_purchases:
            item["item_name"] = self.get_item_name(item.get("item_id"))
        return item_purchases
