import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_REVIEW_STATUSES = {"pending", "confirmed", "rejected"}


def build_review_queue(experiment: dict, summary: dict, ddragon: Any) -> dict:
    """Turn model suggestions into an ID-based queue that requires approval."""
    champion_ids = {}
    item_ids = {}
    for row in summary.get("matches", []):
        champion_id = row.get("champion_id")
        if champion_id:
            official_name = ddragon.get_champion_official_name(champion_id)
            champion_ids.setdefault(official_name, []).append(int(champion_id))
        for item_id in row.get("items", []):
            if item_id:
                item_ids.setdefault(ddragon.get_item_name(item_id), []).append(int(item_id))

    entries = []
    for suggestion in experiment.get("champions", []):
        entity_id = suggestion.get("champion_id") or _resolve_unique_id(
            champion_ids,
            suggestion.get("official_name", ""),
        )
        entries.append(_review_entry("champion", entity_id, suggestion))

    for suggestion in experiment.get("items", []):
        entity_id = suggestion.get("item_id") or _resolve_unique_id(
            item_ids,
            suggestion.get("official_name", ""),
        )
        entries.append(_review_entry("item", entity_id, suggestion))

    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "instructions": {
            "pending": "尚未审核，不会写入术语库",
            "confirmed": "确认 approved_name 后允许写入术语库",
            "rejected": "拒绝该候选，不写入术语库",
        },
        "entries": entries,
    }


def _resolve_unique_id(index: dict[str, list[int]], official_name: str) -> int:
    matches = sorted(set(index.get(official_name, [])))
    if len(matches) != 1:
        raise ValueError(
            f"Could not resolve one Riot ID for official name: {official_name!r}"
        )
    return matches[0]


def _review_entry(entity_type: str, entity_id: int, suggestion: dict) -> dict:
    return {
        "entity_type": entity_type,
        "riot_id": int(entity_id),
        "official_name": suggestion.get("official_name", ""),
        "suggested_name": suggestion.get("natural_name", ""),
        "approved_name": suggestion.get("natural_name", ""),
        "reason": suggestion.get("reason", ""),
        "status": "pending",
    }


def apply_confirmed_reviews(review: dict, terminology: dict) -> tuple[dict, int]:
    """Apply only explicitly confirmed entries and return the updated glossary."""
    updated = json.loads(json.dumps(terminology, ensure_ascii=False))
    updated.setdefault("champions", {})
    updated.setdefault("items", {})
    applied = 0

    for entry in review.get("entries", []):
        status = entry.get("status")
        if status not in VALID_REVIEW_STATUSES:
            raise ValueError(f"Invalid review status: {status!r}")
        if status != "confirmed":
            continue

        approved_name = str(entry.get("approved_name", "")).strip()
        if not approved_name:
            raise ValueError("A confirmed entry must have an approved_name.")
        entity_type = entry.get("entity_type")
        section = {"champion": "champions", "item": "items"}.get(entity_type)
        if not section:
            raise ValueError(f"Invalid entity_type: {entity_type!r}")

        updated[section][str(entry["riot_id"])] = {
            "official_name": entry.get("official_name", ""),
            "preferred_name": approved_name,
            "alternatives": [],
            "status": "confirmed",
            "source": "reviewed_glm_candidate",
        }
        applied += 1

    return updated, applied


def apply_review_decisions(review: dict, decisions: dict) -> tuple[dict, int]:
    """Mark explicitly listed IDs as confirmed and leave all others pending."""
    updated = json.loads(json.dumps(review, ensure_ascii=False))
    decision_maps = {
        "champion": decisions.get("champions", {}),
        "item": decisions.get("items", {}),
    }
    changed = 0
    for entry in updated.get("entries", []):
        names = decision_maps.get(entry.get("entity_type"), {})
        approved_name = names.get(str(entry.get("riot_id")))
        if approved_name:
            entry["approved_name"] = approved_name
            entry["status"] = "confirmed"
            changed += 1
    return updated, changed


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
