import re
from pathlib import Path


SAFE_COMPONENT_PATTERN = re.compile(r"[^0-9A-Za-z._-]+")


def safe_component(value: str) -> str:
    cleaned = SAFE_COMPONENT_PATTERN.sub("_", value.strip()).strip("._-")
    return cleaned or "unknown"


def player_slug(game_name: str, tag_line: str) -> str:
    return f"{safe_component(game_name)}_{safe_component(tag_line)}"


def slug_from_summary(summary: dict) -> str:
    player = summary.get("player") or {}
    return player_slug(
        str(player.get("game_name") or "unknown"),
        str(player.get("tag_line") or "unknown"),
    )


def summary_path(game_name: str, tag_line: str) -> Path:
    return Path("data/cache") / f"player_summary_{player_slug(game_name, tag_line)}.json"


def deterministic_report_path(summary: dict) -> Path:
    return Path("reports") / f"riftcoach_report_{slug_from_summary(summary)}.md"


def coach_report_path(summary: dict) -> Path:
    return Path("reports") / f"riftcoach_coach_report_{slug_from_summary(summary)}.md"


def evaluation_path(report_path: Path) -> Path:
    return report_path.with_suffix(".eval.json")


def revised_report_path(report_path: Path) -> Path:
    return report_path.with_name(f"{report_path.stem}.revised{report_path.suffix}")
