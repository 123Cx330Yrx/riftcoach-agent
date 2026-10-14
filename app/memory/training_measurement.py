"""Deterministic per-match measurements; never infer a metric's sample scope."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.evidence.adapters import EvidenceAdapterError, normalize_riot_position
from app.evidence.summary_bridge import summary_projection_digest
from app.memory.models import CandidateDomainModel

PRODUCER_ID = "training-match-measurement"
PRODUCER_VERSION = "1.0.0"
METRICS = {
    "match.deaths_before_15": ("deaths_before_15", "count"),
    "match.vision_score": ("vision_score", "score"),
}


class MatchMeasurement(CandidateDomainModel):
    scope: Literal["included_match_all_positions"] = "included_match_all_positions"
    source: Literal["riot_match_v5"] = "riot_match_v5"
    match_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
    position: Literal["top", "jungle", "mid", "adc", "support"]
    queue_id: int = Field(ge=0)
    game_end_timestamp_ms: int = Field(gt=0, le=253402300799999)
    summary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary_projection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def observed_at(self) -> datetime:
        return datetime.fromtimestamp(self.game_end_timestamp_ms / 1000, timezone.utc)


def measurement_key(*, owner_id: str, relationship_id: UUID, plan_id: UUID,
                    metric_key: str, match_id: str) -> str:
    identity = [owner_id, str(relationship_id), str(plan_id), metric_key, match_id]
    digest = hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
    return f"training-match-{digest}"


def match_measurements(summary: dict, *, metrics: list[dict], plan_created_at: datetime,
                       task_created_at: datetime, summary_sha256: str) -> tuple[tuple[str, float, MatchMeasurement], ...]:
    """Skip unmeasured rows; duplicate identities invalidate the entire source."""
    rows = summary["matches"]
    ids = [row.get("match_id") for row in rows]
    if any(not isinstance(value, str) for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("training_measurement_match_identity_invalid")
    if len(rows) > 100:
        raise ValueError("training_measurement_sample_bound")
    allowed = [key for key, (_, unit) in METRICS.items()
               if any(item.get("metric_key") == key and item.get("unit") == unit for item in metrics)]
    result = []
    projection_sha = summary_projection_digest(summary)
    for row in sorted(rows, key=lambda item: item["match_id"]):
        if row.get("included_in_aggregate") is not True:
            continue
        try:
            measurement = MatchMeasurement(
                match_id=row["match_id"], position=normalize_riot_position(row.get("role")),
                queue_id=row.get("queue_id"), game_end_timestamp_ms=row.get("game_end_timestamp_ms"),
                summary_sha256=summary_sha256,
                summary_projection_sha256=projection_sha,
            )
            if not plan_created_at <= measurement.observed_at <= task_created_at:
                continue
        except (ValueError, TypeError, EvidenceAdapterError, OverflowError, OSError):
            continue
        for key in allowed:
            field, _ = METRICS[key]
            if field == "deaths_before_15" and row.get("timeline_status") != "available":
                continue
            value = row.get(field)
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or value < 0 or not float(value).is_integer()):
                continue
            result.append((key, float(value), measurement))
    return tuple(result)
