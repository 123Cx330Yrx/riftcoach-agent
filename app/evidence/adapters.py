"""No-I/O adapters from existing RiftCoach source projections.

The functions here deliberately accept already materialized rows.  Network
clients and secrets stay outside the 8D fusion boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .fusion import (
    DataDragonSnapshot,
    RiotMatchEvidence,
)


_PATCH_PREFIX = re.compile(r"^(\d{1,3}\.\d{1,3}(?:\.\d{1,3})?)$")
_ROLE_MAP = {
    "top": "top",
    "jungle": "jungle",
    "middle": "mid",
    "mid": "mid",
    "bottom": "adc",
    "adc": "adc",
    "utility": "support",
    "support": "support",
}


class EvidenceAdapterError(ValueError):
    """Safe, body-free failure at the source-to-evidence seam."""

    def __init__(self, code: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code):
            raise ValueError("invalid adapter error code")
        self.code = code
        super().__init__(code)


def riot_match_from_summary_row(
    row: Mapping[str, Any],
    *,
    routing_region: str,
    source_digest: str | None = None,
    observed_at: datetime | str | None = None,
) -> RiotMatchEvidence:
    """Project one existing Summary row into the strict 8D Riot contract."""

    if not isinstance(row, Mapping):
        raise EvidenceAdapterError("riot_summary_row_invalid")
    required = (
        "match_id",
        "queue_id",
        "champion_id",
        "champion_name",
        "role",
        "win",
        "game_duration_seconds",
        "timeline_status",
    )
    if any(field not in row for field in required):
        raise EvidenceAdapterError("riot_summary_row_invalid")
    if not isinstance(routing_region, str) or not routing_region.strip():
        raise EvidenceAdapterError("riot_region_invalid")
    patch_version = _patch_version(row.get("game_version"))
    projected = {
        "match_id": row.get("match_id"),
        "routing_region": routing_region,
        "queue_id": row.get("queue_id"),
        "champion_id": row.get("champion_id"),
        "champion_name": row.get("champion_name"),
        "position": _position(row.get("role")),
        "patch_version": patch_version,
        "win": row.get("win"),
        "duration_seconds": row.get("game_duration_seconds"),
        "timeline_available": row.get("timeline_status") == "available",
        "observed_at": _observed_at(
            observed_at
            or row.get("observed_at")
            or row.get("generated_at_utc")
        ),
    }
    digest = source_digest or _digest(projected)
    try:
        return RiotMatchEvidence(
            **projected,
            source_digest=digest,
        )
    except (TypeError, ValueError):
        raise EvidenceAdapterError("riot_summary_row_invalid") from None


def data_dragon_snapshot_from_identity(
    *,
    version: str,
    language: str,
    catalog_digest: str,
    retrieved_at,
) -> DataDragonSnapshot:
    """Build a static snapshot identity without loading or fetching a catalog."""

    try:
        return DataDragonSnapshot(
            version=version,
            language=language,
            catalog_digest=catalog_digest,
            retrieved_at=retrieved_at,
        )
    except (TypeError, ValueError):
        raise EvidenceAdapterError("data_dragon_identity_invalid") from None


def _patch_version(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise EvidenceAdapterError("riot_patch_invalid")
    match = _PATCH_PREFIX.fullmatch(value.strip())
    if match is None:
        raise EvidenceAdapterError("riot_patch_invalid")
    parts = match.group(1).split(".")
    return ".".join(parts[:2])


def _observed_at(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    raise EvidenceAdapterError("riot_observed_at_invalid")


def _position(value: object) -> str:
    if not isinstance(value, str):
        raise EvidenceAdapterError("riot_position_invalid")
    normalized = _ROLE_MAP.get(value.strip().casefold())
    if normalized is None:
        raise EvidenceAdapterError("riot_position_invalid")
    return normalized


def _digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "EvidenceAdapterError",
    "data_dragon_snapshot_from_identity",
    "riot_match_from_summary_row",
]
