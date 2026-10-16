"""Separate observed match roles from explicitly declared training goals.

This is a projection of the supplied sample, not a long-term player profile.
It never infers autofill intent or overwrites an observed role with a goal.
"""

from collections.abc import Mapping
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.evidence.adapters import EvidenceAdapterError, normalize_riot_position


Position = Literal["top", "jungle", "mid", "adc", "support"]
POSITIONS = ("top", "jungle", "mid", "adc", "support")


def validate_training_positions(values: tuple[str, ...]) -> tuple[str, ...]:
    if (not isinstance(values, tuple) or len(values) > 5
            or any(value not in POSITIONS for value in values)
            or len(set(values)) != len(values)):
        raise ValueError("training_positions_invalid")
    return values


class PositionSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    position: Position
    games: int
    champions: tuple[str, ...]
    averages: dict[str, float | None]
    metric_sample_counts: dict[str, int]


class CoachPositionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_scope: Literal["selected_matches_only"] = "selected_matches_only"
    observed: tuple[PositionSample, ...]
    unknown_position_games: int
    excluded_games: int
    training_positions: tuple[Position, ...]
    goal_source: Literal["explicit_request", "unspecified"]
    long_term_main_position: None = None
    autofill_intent: Literal["unknown"] = "unknown"


def position_context(
    summary: Mapping[str, Any], *, training_positions: tuple[str, ...] = (),
) -> CoachPositionContext:
    goals = validate_training_positions(training_positions)
    groups: dict[str, list[Mapping[str, Any]]] = {}
    unknown = excluded = 0
    for row in summary["matches"]:
        if row.get("included_in_aggregate") is not True:
            excluded += 1
            continue
        try:
            role = normalize_riot_position(row.get("role"))
        except EvidenceAdapterError:
            unknown += 1
            continue
        champion = row.get("champion_name_en") or row.get("champion_name")
        if not isinstance(champion, str) or not champion.strip():
            raise ValueError("match_champion_missing")
        groups.setdefault(role, []).append(row)
    samples = []
    for role in POSITIONS:
        rows = groups.get(role)
        if not rows:
            continue
        champions = {}
        for row in rows:
            name = (row.get("champion_name_en") or row["champion_name"]).strip()
            champions.setdefault(name.casefold(), name)
        averages, counts = {}, {}
        for metric in ("cs_per_min", "gold_per_min", "deaths_before_15", "vision_score"):
            values = [row.get(metric) for row in rows]
            values = [value for value in values if isinstance(value, (int, float))
                      and not isinstance(value, bool) and math.isfinite(value) and value >= 0]
            counts[metric] = len(values)
            averages[metric] = round(sum(values) / len(values), 4) if values else None
        samples.append(PositionSample(position=role, games=len(rows), champions=tuple(champions.values()),
                                      averages=averages, metric_sample_counts=counts))
    return CoachPositionContext(
        observed=tuple(samples),
        unknown_position_games=unknown, excluded_games=excluded,
        training_positions=goals,
        goal_source="explicit_request" if goals else "unspecified",
    )
