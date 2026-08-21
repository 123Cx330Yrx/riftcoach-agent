"""Source-labelled, immutable evidence for dynamic game Meta.

Meta is an external comparison dataset, not a replacement for Riot facts or
long-lived player Memory.  Every evidence value therefore carries an explicit
provenance grade and a bounded set of uses.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CHAMPION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .'&-]{0,63}$")
_INSTRUCTION_WORDS = frozenset(
    {"assistant", "ignore", "instruction", "prompt", "system", "user"}
)
_POSITION_VALUES = frozenset({"top", "mid", "jungle", "adc", "support"})


class MetaProvenance(str, Enum):
    """How completely the upstream source identifies its snapshot."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class MetaUseCase(str, Enum):
    """Claims that a caller may ask one Meta snapshot to support."""

    CURRENT_SNAPSHOT_RECOMMENDATION = "current_snapshot_recommendation"
    EXACT_PATCH_ATTRIBUTION = "exact_patch_attribution"
    HISTORICAL_PATCH_COMPARISON = "historical_patch_comparison"
    UPSTREAM_FRESHNESS_CLAIM = "upstream_freshness_claim"


def _utc(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field_name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class LaneMetaChampionFact:
    """One allowlisted row from an OP.GG lane-Meta snapshot."""

    champion: str
    win_rate: float
    pick_rate: float
    ban_rate: float
    tier: int
    rank: int
    rank_previous: int | None
    rank_previous_patch: int | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.champion, str)
            or self.champion != self.champion.strip()
            or not _CHAMPION_PATTERN.fullmatch(self.champion)
            or _INSTRUCTION_WORDS.intersection(
                re.findall(r"[a-z]+", self.champion.casefold())
            )
        ):
            raise ValueError("champion name is invalid")
        for field_name in ("win_rate", "pick_rate", "ban_rate"):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not 0.0 <= float(value) <= 1.0
            ):
                raise ValueError(f"{field_name} must be between zero and one")
            object.__setattr__(self, field_name, float(value))
        if (
            isinstance(self.tier, bool)
            or not isinstance(self.tier, int)
            or not 0 <= self.tier <= 10
        ):
            raise ValueError("tier must be an integer between zero and ten")
        if (
            isinstance(self.rank, bool)
            or not isinstance(self.rank, int)
            or self.rank <= 0
        ):
            raise ValueError("rank must be a positive integer")
        for field_name in ("rank_previous", "rank_previous_patch"):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"{field_name} must be a positive integer or None")

    def to_dict(self) -> dict[str, object]:
        return {
            "champion": self.champion,
            "win_rate": self.win_rate,
            "pick_rate": self.pick_rate,
            "ban_rate": self.ban_rate,
            "tier": self.tier,
            "rank": self.rank,
            "rank_previous": self.rank_previous,
            "rank_previous_patch": self.rank_previous_patch,
        }


@dataclass(frozen=True)
class MetaEvidence:
    """A bounded snapshot whose digest covers facts and provenance."""

    source: str
    remote_tool: str
    position: str
    facts: tuple[LaneMetaChampionFact, ...] = field(repr=False)
    provenance: MetaProvenance
    upstream_patch: str | None
    source_generated_at: datetime | None
    retrieved_at: datetime
    expires_at: datetime
    allowed_uses: frozenset[MetaUseCase]
    catalog_digest: str
    tool_schema_digest: str
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if self.source != "opgg":
            raise ValueError("source must be opgg")
        if not isinstance(self.remote_tool, str) or not self.remote_tool.strip():
            raise ValueError("remote_tool must not be blank")
        if self.position not in _POSITION_VALUES:
            raise ValueError("position is invalid")
        if (
            not isinstance(self.facts, tuple)
            or not self.facts
            or len(self.facts) > 10
            or not all(isinstance(fact, LaneMetaChampionFact) for fact in self.facts)
        ):
            raise ValueError("facts must contain one to ten lane Meta facts")
        if len({fact.champion.casefold() for fact in self.facts}) != len(self.facts):
            raise ValueError("champion facts must be unique")
        if len({fact.rank for fact in self.facts}) != len(self.facts):
            raise ValueError("lane Meta ranks must be unique")
        if not isinstance(self.provenance, MetaProvenance):
            raise ValueError("provenance must be MetaProvenance")
        if self.upstream_patch is not None and (
            not isinstance(self.upstream_patch, str)
            or not self.upstream_patch.strip()
            or len(self.upstream_patch) > 64
        ):
            raise ValueError("upstream_patch must be bounded text or None")
        source_generated_at = (
            _utc(self.source_generated_at, field_name="source_generated_at")
            if self.source_generated_at is not None
            else None
        )
        retrieved_at = _utc(self.retrieved_at, field_name="retrieved_at")
        expires_at = _utc(self.expires_at, field_name="expires_at")
        if expires_at <= retrieved_at:
            raise ValueError("expires_at must be after retrieved_at")
        object.__setattr__(self, "source_generated_at", source_generated_at)
        object.__setattr__(self, "retrieved_at", retrieved_at)
        object.__setattr__(self, "expires_at", expires_at)
        if (
            not isinstance(self.allowed_uses, frozenset)
            or not self.allowed_uses
            or not all(isinstance(item, MetaUseCase) for item in self.allowed_uses)
        ):
            raise ValueError("allowed_uses must be a non-empty MetaUseCase frozenset")
        if self.provenance is MetaProvenance.PARTIAL:
            if self.upstream_patch is not None or self.source_generated_at is not None:
                raise ValueError("partial provenance cannot invent patch or source time")
            if self.allowed_uses != frozenset(
                {MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION}
            ):
                raise ValueError("partial provenance only supports current snapshots")
        elif self.upstream_patch is None or self.source_generated_at is None:
            raise ValueError(
                "complete provenance requires patch and source time"
            )
        for field_name in ("catalog_digest", "tool_schema_digest"):
            if not _DIGEST_PATTERN.fullmatch(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be a SHA-256 digest")
        object.__setattr__(self, "digest", self._calculate_digest())

    def _projection(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "source": self.source,
            "remote_tool": self.remote_tool,
            "position": self.position,
            "provenance": self.provenance.value,
            "upstream_patch": self.upstream_patch,
            "source_generated_at": _timestamp(self.source_generated_at),
            "retrieved_at": _timestamp(self.retrieved_at),
            "expires_at": _timestamp(self.expires_at),
            "allowed_uses": sorted(item.value for item in self.allowed_uses),
            "catalog_digest": self.catalog_digest,
            "tool_schema_digest": self.tool_schema_digest,
            "facts": [fact.to_dict() for fact in self.facts],
        }

    def _calculate_digest(self) -> str:
        encoded = json.dumps(
            self._projection(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {**self._projection(), "digest": self.digest}

    def require_usable(self, use_case: MetaUseCase, *, now: datetime) -> None:
        if not isinstance(use_case, MetaUseCase):
            raise TypeError("use_case must be MetaUseCase")
        checked_at = _utc(now, field_name="now")
        if use_case not in self.allowed_uses:
            raise ValueError("Meta evidence is not allowed for this use case")
        if checked_at >= self.expires_at:
            raise ValueError("Meta evidence is expired")
