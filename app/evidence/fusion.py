"""Deterministic, provenance-aware Riot + OP.GG evidence fusion.

This module is deliberately an anti-corruption boundary.  It accepts typed
snapshots produced by source adapters and returns an immutable bundle; it does
not construct clients, read secrets, or perform network/MCP/Provider I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.meta.models import MetaEvidence, MetaProvenance, MetaUseCase


_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_PATCH_PATTERN = r"^[0-9]{1,3}\.[0-9]{1,3}(?:\.[0-9]{1,3})?$"
_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_INSTRUCTION_WORDS = frozenset(
    {"assistant", "ignore", "instruction", "prompt", "system", "user"}
)

Sha256Text = Annotated[
    str,
    StringConstraints(min_length=64, max_length=64, pattern=_DIGEST_PATTERN),
]
SafeIdentifier = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=_ID_PATTERN),
]
PatchVersion = Annotated[
    str,
    StringConstraints(min_length=3, max_length=32, pattern=_PATCH_PATTERN),
]
RoutingRegion = Annotated[
    str,
    StringConstraints(
        min_length=2,
        max_length=16,
        pattern=r"^[a-z][a-z0-9_-]{1,15}$",
    ),
]
Position = Literal["top", "mid", "jungle", "adc", "support"]


class EvidenceModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class EvidenceSource(StrEnum):
    RIOT_OFFICIAL = "riot_official"
    DATA_DRAGON = "data_dragon"
    RIOT_PATCH = "riot_patch"
    OPGG = "opgg"


class EvidenceFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class EvidenceBundleDisposition(StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    REJECTED = "rejected"


class EvidenceConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class EvidenceClaim(StrEnum):
    RIOT_MATCH_FACTS = "riot_match_facts"
    DATA_DRAGON_STATIC = "data_dragon_static"
    OFFICIAL_PATCH_FACTS = "official_patch_facts"
    CURRENT_META_RECOMMENDATION = "current_meta_recommendation"
    EXACT_PATCH_META_COMPARISON = "exact_patch_meta_comparison"


class EvidenceJoinStatus(StrEnum):
    JOINED = "joined"
    JOINED_PARTIAL = "joined_partial"
    UNJOINED = "unjoined"
    STALE = "stale"
    CONFLICT = "conflict"


class RiotMatchEvidence(EvidenceModel):
    """Allowlisted facts from one Riot Match-V5 response."""

    source: Literal[EvidenceSource.RIOT_OFFICIAL] = EvidenceSource.RIOT_OFFICIAL
    match_id: SafeIdentifier
    routing_region: RoutingRegion
    queue_id: int = Field(gt=0, le=10_000)
    champion_id: int = Field(gt=0, le=10_000)
    champion_name: str
    position: Position
    patch_version: PatchVersion | None
    win: bool
    duration_seconds: int = Field(gt=0, le=24 * 60 * 60)
    timeline_available: bool
    observed_at: datetime
    source_digest: Sha256Text

    @field_validator("champion_name")
    @classmethod
    def validate_champion_name(cls, value: str) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
            or not _safe_label(value)
            or _INSTRUCTION_WORDS.intersection(
                re.findall(r"[a-z]+", value.casefold())
            )
        ):
            raise ValueError("champion_name is not a safe label")
        return value.strip()

    @field_validator("patch_version")
    @classmethod
    def normalize_patch_version(cls, value: str | None) -> str | None:
        return None if value is None else value.strip()

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return _as_utc(value, field_name="observed_at")


class DataDragonSnapshot(EvidenceModel):
    """One versioned Data Dragon static catalog identity."""

    source: Literal[EvidenceSource.DATA_DRAGON] = EvidenceSource.DATA_DRAGON
    version: PatchVersion
    language: str = Field(min_length=2, max_length=16, pattern=r"^[a-z]{2}_[A-Z]{2}$")
    catalog_digest: Sha256Text
    retrieved_at: datetime

    @field_validator("retrieved_at")
    @classmethod
    def normalize_retrieved_at(cls, value: datetime) -> datetime:
        return _as_utc(value, field_name="retrieved_at")


class OfficialPatchEvidence(EvidenceModel):
    """Version/update fact from an official Riot patch source."""

    source: Literal[EvidenceSource.RIOT_PATCH] = EvidenceSource.RIOT_PATCH
    patch_version: PatchVersion
    update_id: SafeIdentifier
    published_at: datetime
    retrieved_at: datetime
    expires_at: datetime | None
    source_digest: Sha256Text

    @field_validator("published_at", "retrieved_at", "expires_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value, field_name="timestamp")

    @model_validator(mode="after")
    def validate_timeline(self) -> Self:
        if self.published_at > self.retrieved_at:
            raise ValueError("patch cannot be retrieved before publication")
        if self.expires_at is not None and self.expires_at <= self.retrieved_at:
            raise ValueError("patch expiry must follow retrieval")
        return self


class EvidenceJoinKey(EvidenceModel):
    """Explicit dimensions used to compare facts from different sources."""

    routing_region: RoutingRegion
    queue_id: int = Field(gt=0, le=10_000)
    position: Position
    champion_name: str
    patch_version: PatchVersion | None

    @field_validator("champion_name")
    @classmethod
    def validate_champion_name(cls, value: str) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
            or not _safe_label(value)
        ):
            raise ValueError("champion_name is not a safe label")
        return value.strip()

    @property
    def normalized_champion(self) -> str:
        return self.champion_name.casefold()

    @property
    def digest(self) -> str:
        payload = json.dumps(
            self.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "routing_region": self.routing_region,
            "queue_id": self.queue_id,
            "position": self.position,
            "champion_name": self.champion_name,
            "patch_version": self.patch_version,
        }


class EvidenceJoin(EvidenceModel):
    key: EvidenceJoinKey
    status: EvidenceJoinStatus
    confidence: EvidenceConfidence
    riot_match_id: SafeIdentifier
    riot_source_digest: Sha256Text
    data_dragon_digest: Sha256Text | None
    official_patch_digest: Sha256Text | None
    opgg_meta_digest: Sha256Text | None


class EvidenceConflict(EvidenceModel):
    code: Annotated[
        str,
        StringConstraints(
            min_length=1,
            max_length=64,
            pattern=r"^[a-z][a-z0-9_]{0,63}$",
        ),
    ]
    sources: tuple[EvidenceSource, ...] = Field(min_length=2, max_length=4)
    key: EvidenceJoinKey | None
    source_digests: tuple[Sha256Text, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_sources(self) -> Self:
        if len(set(self.sources)) != len(self.sources):
            raise ValueError("conflict sources must be unique")
        if len(set(self.source_digests)) != len(self.source_digests):
            raise ValueError("conflict source digests must be unique")
        return self


class EvidenceGap(EvidenceModel):
    code: Annotated[
        str,
        StringConstraints(
            min_length=1,
            max_length=64,
            pattern=r"^[a-z][a-z0-9_]{0,63}$",
        ),
    ]
    source: EvidenceSource
    key: EvidenceJoinKey | None
    source_digest: Sha256Text | None


class EvidenceBundle(EvidenceModel):
    """Immutable result of the deterministic fusion kernel."""

    schema_version: Literal["1.0"] = "1.0"
    riot_matches: tuple[RiotMatchEvidence, ...]
    data_dragon: DataDragonSnapshot | None
    official_patch: OfficialPatchEvidence | None
    # Pydantic's dataclass adapter treats MetaEvidence's init=False digest as
    # a constructor field. Keep the already-validated immutable dataclass as
    # an opaque value and validate the boundary explicitly below.
    meta_evidence: tuple[Any, ...]
    joins: tuple[EvidenceJoin, ...]
    conflicts: tuple[EvidenceConflict, ...]
    gaps: tuple[EvidenceGap, ...]
    claims: tuple[EvidenceClaim, ...]
    disposition: EvidenceBundleDisposition
    confidence: EvidenceConfidence
    created_at: datetime
    digest: Sha256Text = Field(default="0" * 64)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value, field_name="created_at")

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        if not all(isinstance(row, MetaEvidence) for row in self.meta_evidence):
            raise TypeError("meta_evidence must contain MetaEvidence values")
        match_ids = tuple(row.match_id for row in self.riot_matches)
        if len(set(match_ids)) != len(match_ids):
            raise ValueError("bundle contains duplicate Riot match ids")
        if len(self.joins) != len(self.riot_matches):
            raise ValueError("bundle must contain one join per Riot match")
        if tuple(join.riot_match_id for join in self.joins) != match_ids:
            raise ValueError("bundle joins must follow Riot match order")
        if not self.riot_matches and self.disposition is not EvidenceBundleDisposition.REJECTED:
            raise ValueError("empty bundle must be rejected")
        if self.disposition is EvidenceBundleDisposition.REJECTED and self.claims:
            raise ValueError("rejected bundle cannot expose claims")
        if self.disposition is EvidenceBundleDisposition.COMPLETE and (
            self.gaps or self.conflicts
        ):
            raise ValueError("complete bundle cannot contain gaps or conflicts")
        if EvidenceClaim.EXACT_PATCH_META_COMPARISON in self.claims:
            if self.official_patch is None or self.conflicts:
                raise ValueError("exact-patch claim requires an unconflicted official patch")
            if not any(
                evidence.provenance is MetaProvenance.COMPLETE
                and MetaUseCase.EXACT_PATCH_ATTRIBUTION in evidence.allowed_uses
                for evidence in self.meta_evidence
            ):
                raise ValueError("exact-patch claim requires complete Meta provenance")
        object.__setattr__(self, "digest", self.computed_digest())
        return self

    def _projection(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "riot_matches": [
                {
                    "source": row.source.value,
                    "match_id": row.match_id,
                    "routing_region": row.routing_region,
                    "queue_id": row.queue_id,
                    "champion_id": row.champion_id,
                    "champion_name": row.champion_name,
                    "position": row.position,
                    "patch_version": row.patch_version,
                    "win": row.win,
                    "duration_seconds": row.duration_seconds,
                    "timeline_available": row.timeline_available,
                    "observed_at": _timestamp(row.observed_at),
                    "source_digest": row.source_digest,
                }
                for row in self.riot_matches
            ],
            "data_dragon": (
                None
                if self.data_dragon is None
                else {
                    "source": self.data_dragon.source.value,
                    "version": self.data_dragon.version,
                    "language": self.data_dragon.language,
                    "catalog_digest": self.data_dragon.catalog_digest,
                    "retrieved_at": _timestamp(self.data_dragon.retrieved_at),
                }
            ),
            "official_patch": (
                None
                if self.official_patch is None
                else {
                    "source": self.official_patch.source.value,
                    "patch_version": self.official_patch.patch_version,
                    "update_id": self.official_patch.update_id,
                    "published_at": _timestamp(self.official_patch.published_at),
                    "retrieved_at": _timestamp(self.official_patch.retrieved_at),
                    "expires_at": _timestamp(self.official_patch.expires_at),
                    "source_digest": self.official_patch.source_digest,
                }
            ),
            "meta_evidence": [
                {
                    "source": evidence.source,
                    "remote_tool": evidence.remote_tool,
                    "position": evidence.position,
                    "provenance": evidence.provenance.value,
                    "upstream_patch": evidence.upstream_patch,
                    "source_generated_at": _timestamp(evidence.source_generated_at),
                    "retrieved_at": _timestamp(evidence.retrieved_at),
                    "expires_at": _timestamp(evidence.expires_at),
                    "allowed_uses": sorted(item.value for item in evidence.allowed_uses),
                    "catalog_digest": evidence.catalog_digest,
                    "tool_schema_digest": evidence.tool_schema_digest,
                    "digest": evidence.digest,
                }
                for evidence in self.meta_evidence
            ],
            "joins": [
                {
                    "key": join.key.to_dict(),
                    "status": join.status.value,
                    "confidence": join.confidence.value,
                    "riot_match_id": join.riot_match_id,
                    "riot_source_digest": join.riot_source_digest,
                    "data_dragon_digest": join.data_dragon_digest,
                    "official_patch_digest": join.official_patch_digest,
                    "opgg_meta_digest": join.opgg_meta_digest,
                }
                for join in self.joins
            ],
            "conflicts": [
                {
                    "code": conflict.code,
                    "sources": sorted(source.value for source in conflict.sources),
                    "key": None if conflict.key is None else conflict.key.to_dict(),
                    "source_digests": sorted(conflict.source_digests),
                }
                for conflict in self.conflicts
            ],
            "gaps": [
                {
                    "code": gap.code,
                    "source": gap.source.value,
                    "key": None if gap.key is None else gap.key.to_dict(),
                    "source_digest": gap.source_digest,
                }
                for gap in self.gaps
            ],
            "claims": sorted(claim.value for claim in self.claims),
            "disposition": self.disposition.value,
            "confidence": self.confidence.value,
            "created_at": _timestamp(self.created_at),
        }

    def computed_digest(self) -> str:
        encoded = json.dumps(
            self._projection(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_storage_projection(self) -> dict[str, object]:
        """Return the full typed, body-free projection needed for rehydration.

        The canonical bundle digest deliberately binds each Meta snapshot by its
        own digest.  Persistence additionally needs the allowlisted Meta facts so
        the dataclass can be rebuilt and that nested digest can be recomputed.
        """

        projection = self._projection()
        projection["claims"] = [claim.value for claim in self.claims]
        projection["meta_evidence"] = [
            {
                **row,
                "facts": [fact.to_dict() for fact in evidence.facts],
            }
            for row, evidence in zip(
                projection["meta_evidence"],
                self.meta_evidence,
                strict=True,
            )
        ]
        return {**projection, "digest": self.digest}

    def has_valid_digest(self) -> bool:
        return self.digest == self.computed_digest()

    def to_public_projection(self) -> dict[str, object]:
        """Return an allowlisted, body-free projection for later UI/Context use."""

        sources = {
            "riot_official": {
                "match_count": len(self.riot_matches),
                "digests": sorted(row.source_digest for row in self.riot_matches),
                "freshness": EvidenceFreshness.CURRENT.value
                if self.riot_matches
                else EvidenceFreshness.UNKNOWN.value,
            },
            "data_dragon": {
                "version": None if self.data_dragon is None else self.data_dragon.version,
                "catalog_digest": (
                    None
                    if self.data_dragon is None
                    else self.data_dragon.catalog_digest
                ),
                "freshness": _data_dragon_freshness(self),
            },
            "riot_patch": {
                "patch_version": (
                    None
                    if self.official_patch is None
                    else self.official_patch.patch_version
                ),
                "source_digest": (
                    None
                    if self.official_patch is None
                    else self.official_patch.source_digest
                ),
                "freshness": _patch_freshness(self),
            },
            "opgg": {
                "evidence_count": len(self.meta_evidence),
                "digests": sorted(row.digest for row in self.meta_evidence),
                "provenance": sorted(
                    row.provenance.value for row in self.meta_evidence
                ),
                "freshness": _meta_freshness(self),
            },
        }
        return {
            "schema_version": self.schema_version,
            "bundle_digest": self.digest,
            "disposition": self.disposition.value,
            "confidence": self.confidence.value,
            "claims": sorted(claim.value for claim in self.claims),
            "matches": [
                {
                    "match_id": row.match_id,
                    "champion_name": row.champion_name,
                    "position": row.position,
                    "patch_version": row.patch_version,
                    "win": row.win,
                    "timeline_available": row.timeline_available,
                }
                for row in self.riot_matches
            ],
            "joins": [
                {
                    "key": join.key.to_dict(),
                    "status": join.status.value,
                    "confidence": join.confidence.value,
                    "sources_present": {
                        "riot": True,
                        "data_dragon": join.data_dragon_digest is not None,
                        "riot_patch": join.official_patch_digest is not None,
                        "opgg": join.opgg_meta_digest is not None,
                    },
                }
                for join in self.joins
            ],
            "conflicts": [
                {
                    "code": conflict.code,
                    "sources": sorted(source.value for source in conflict.sources),
                    "key": None if conflict.key is None else conflict.key.to_dict(),
                }
                for conflict in self.conflicts
            ],
            "gaps": [
                {
                    "code": gap.code,
                    "source": gap.source.value,
                    "key": None if gap.key is None else gap.key.to_dict(),
                }
                for gap in self.gaps
            ],
            "sources": sources,
        }


def fuse_evidence(
    *,
    riot_matches: tuple[RiotMatchEvidence, ...] | list[RiotMatchEvidence],
    data_dragon: DataDragonSnapshot | None,
    official_patch: OfficialPatchEvidence | None,
    meta_evidence: tuple[MetaEvidence, ...] | list[MetaEvidence],
    now: datetime,
) -> EvidenceBundle:
    """Fuse typed snapshots without performing any external I/O."""

    if not isinstance(riot_matches, (tuple, list)) or not all(
        isinstance(row, RiotMatchEvidence) for row in riot_matches
    ):
        raise TypeError("riot_matches must contain RiotMatchEvidence values")
    if not isinstance(meta_evidence, (tuple, list)) or not all(
        isinstance(row, MetaEvidence) for row in meta_evidence
    ):
        raise TypeError("meta_evidence must contain MetaEvidence values")
    checked_now = _as_utc(now, field_name="now")
    matches = tuple(riot_matches)
    metas = tuple(meta_evidence)
    if len({row.match_id for row in matches}) != len(matches):
        raise ValueError("duplicate Riot match id")

    if not matches:
        return EvidenceBundle(
            riot_matches=(),
            data_dragon=data_dragon,
            official_patch=official_patch,
            meta_evidence=metas,
            joins=(),
            conflicts=(),
            gaps=(
                EvidenceGap(
                    code="riot_match_missing",
                    source=EvidenceSource.RIOT_OFFICIAL,
                    key=None,
                    source_digest=None,
                ),
            ),
            claims=(),
            disposition=EvidenceBundleDisposition.REJECTED,
            confidence=EvidenceConfidence.UNKNOWN,
            created_at=checked_now,
        )

    joins: list[EvidenceJoin] = []
    conflicts: list[EvidenceConflict] = []
    gaps: list[EvidenceGap] = []
    current_meta_joined = False
    exact_meta_joined = False

    for match in matches:
        key = EvidenceJoinKey(
            routing_region=match.routing_region,
            queue_id=match.queue_id,
            position=match.position,
            champion_name=match.champion_name,
            patch_version=match.patch_version,
        )
        row_conflicts: list[EvidenceConflict] = []
        if match.patch_version is None:
            gaps.append(
                EvidenceGap(
                    code="riot_patch_missing",
                    source=EvidenceSource.RIOT_OFFICIAL,
                    key=key,
                    source_digest=match.source_digest,
                )
            )
        if data_dragon is None:
            gaps.append(
                EvidenceGap(
                    code="data_dragon_missing",
                    source=EvidenceSource.DATA_DRAGON,
                    key=key,
                    source_digest=None,
                )
            )
        elif match.patch_version is not None and not _same_patch(
            match.patch_version, data_dragon.version
        ):
            row_conflicts.append(
                EvidenceConflict(
                    code="data_dragon_patch_mismatch",
                    sources=(EvidenceSource.RIOT_OFFICIAL, EvidenceSource.DATA_DRAGON),
                    key=key,
                    source_digests=(match.source_digest, data_dragon.catalog_digest),
                )
            )
        if official_patch is None:
            gaps.append(
                EvidenceGap(
                    code="official_patch_missing",
                    source=EvidenceSource.RIOT_PATCH,
                    key=key,
                    source_digest=None,
                )
            )
        elif match.patch_version is not None and not _same_patch(
            match.patch_version, official_patch.patch_version
        ):
            row_conflicts.append(
                EvidenceConflict(
                    code="riot_patch_mismatch",
                    sources=(EvidenceSource.RIOT_OFFICIAL, EvidenceSource.RIOT_PATCH),
                    key=key,
                    source_digests=(match.source_digest, official_patch.source_digest),
                )
            )
        if official_patch is not None and official_patch.expires_at is not None and checked_now >= official_patch.expires_at:
            gaps.append(
                EvidenceGap(
                    code="official_patch_stale",
                    source=EvidenceSource.RIOT_PATCH,
                    key=key,
                    source_digest=official_patch.source_digest,
                )
            )

        candidate = _find_meta(metas, match)
        opgg_digest: str | None = None
        status = EvidenceJoinStatus.UNJOINED
        confidence = EvidenceConfidence.LOW
        if candidate is None:
            gaps.append(
                EvidenceGap(
                    code="meta_join_missing",
                    source=EvidenceSource.OPGG,
                    key=key,
                    source_digest=None,
                )
            )
        else:
            try:
                candidate.require_usable(
                    MetaUseCase.CURRENT_SNAPSHOT_RECOMMENDATION,
                    now=checked_now,
                )
            except ValueError:
                status = EvidenceJoinStatus.STALE
                gaps.append(
                    EvidenceGap(
                        code="opgg_meta_expired",
                        source=EvidenceSource.OPGG,
                        key=key,
                        source_digest=candidate.digest,
                    )
                )
            else:
                opgg_digest = candidate.digest
                current_meta_joined = True
                if candidate.provenance is MetaProvenance.PARTIAL:
                    status = EvidenceJoinStatus.JOINED_PARTIAL
                    confidence = EvidenceConfidence.MEDIUM
                else:
                    status = EvidenceJoinStatus.JOINED
                    confidence = EvidenceConfidence.HIGH
                    if (
                        match.patch_version is not None
                        and candidate.upstream_patch is not None
                        and _same_patch(match.patch_version, candidate.upstream_patch)
                    ):
                        exact_meta_joined = True
                    elif candidate.upstream_patch != match.patch_version:
                        row_conflicts.append(
                            EvidenceConflict(
                                code="meta_patch_mismatch",
                                sources=(EvidenceSource.RIOT_OFFICIAL, EvidenceSource.OPGG),
                                key=key,
                                source_digests=(match.source_digest, candidate.digest),
                            )
                        )

        conflicts.extend(row_conflicts)
        if row_conflicts:
            status = EvidenceJoinStatus.CONFLICT
            confidence = EvidenceConfidence.LOW
        joins.append(
            EvidenceJoin(
                key=key,
                status=status,
                confidence=confidence,
                riot_match_id=match.match_id,
                riot_source_digest=match.source_digest,
                data_dragon_digest=(
                    None if data_dragon is None else data_dragon.catalog_digest
                ),
                official_patch_digest=(
                    None
                    if official_patch is None
                    else official_patch.source_digest
                ),
                opgg_meta_digest=opgg_digest,
            )
        )

    claims: list[EvidenceClaim] = [EvidenceClaim.RIOT_MATCH_FACTS]
    if data_dragon is not None:
        claims.append(EvidenceClaim.DATA_DRAGON_STATIC)
    if official_patch is not None:
        claims.append(EvidenceClaim.OFFICIAL_PATCH_FACTS)
    if current_meta_joined:
        claims.append(EvidenceClaim.CURRENT_META_RECOMMENDATION)
    if exact_meta_joined and not conflicts:
        claims.append(EvidenceClaim.EXACT_PATCH_META_COMPARISON)

    disposition = (
        EvidenceBundleDisposition.COMPLETE
        if not gaps and not conflicts
        else EvidenceBundleDisposition.DEGRADED
    )
    if disposition is EvidenceBundleDisposition.COMPLETE:
        confidence = (
            EvidenceConfidence.MEDIUM
            if any(
                evidence.provenance is MetaProvenance.PARTIAL
                for evidence in metas
            )
            else EvidenceConfidence.HIGH
        )
    elif conflicts:
        confidence = EvidenceConfidence.LOW
    else:
        confidence = EvidenceConfidence.MEDIUM
    return EvidenceBundle(
        riot_matches=matches,
        data_dragon=data_dragon,
        official_patch=official_patch,
        meta_evidence=metas,
        joins=tuple(joins),
        conflicts=tuple(conflicts),
        gaps=tuple(gaps),
        claims=tuple(dict.fromkeys(claims)),
        disposition=disposition,
        confidence=confidence,
        created_at=checked_now,
    )


def _find_meta(
    evidence: tuple[MetaEvidence, ...],
    match: RiotMatchEvidence,
) -> MetaEvidence | None:
    candidates = [
        item
        for item in evidence
        if item.position == match.position
        and any(
            fact.champion.casefold() == match.champion_name.casefold()
            for fact in item.facts
        )
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.retrieved_at, item.digest))[-1]


def _same_patch(left: str, right: str) -> bool:
    return ".".join(left.split(".")[:2]) == ".".join(right.split(".")[:2])


def _as_utc(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime | None) -> str | None:
    return None if value is None else _as_utc(value, field_name="timestamp").isoformat().replace("+00:00", "Z")


def _safe_label(value: str) -> bool:
    normalized = value.strip()
    if len(normalized) > 64 or any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        return False
    return bool(normalized) and not _INSTRUCTION_WORDS.intersection(
        re.findall(r"[a-z]+", normalized.casefold())
    )


def _data_dragon_freshness(bundle: EvidenceBundle) -> str:
    if bundle.data_dragon is None:
        return EvidenceFreshness.UNKNOWN.value
    if bundle.official_patch is None:
        return EvidenceFreshness.UNKNOWN.value
    if _same_patch(bundle.data_dragon.version, bundle.official_patch.patch_version):
        return EvidenceFreshness.CURRENT.value
    return EvidenceFreshness.STALE.value


def _patch_freshness(bundle: EvidenceBundle) -> str:
    patch = bundle.official_patch
    if patch is None:
        return EvidenceFreshness.UNKNOWN.value
    if patch.expires_at is not None and bundle.created_at >= patch.expires_at:
        return EvidenceFreshness.STALE.value
    return EvidenceFreshness.CURRENT.value


def _meta_freshness(bundle: EvidenceBundle) -> str:
    if not bundle.meta_evidence:
        return EvidenceFreshness.UNKNOWN.value
    if any(bundle.created_at < item.expires_at for item in bundle.meta_evidence):
        return EvidenceFreshness.CURRENT.value
    return EvidenceFreshness.STALE.value


__all__ = [
    "DataDragonSnapshot",
    "EvidenceBundle",
    "EvidenceBundleDisposition",
    "EvidenceClaim",
    "EvidenceConfidence",
    "EvidenceConflict",
    "EvidenceFreshness",
    "EvidenceJoin",
    "EvidenceJoinKey",
    "EvidenceJoinStatus",
    "EvidenceSource",
    "OfficialPatchEvidence",
    "RiotMatchEvidence",
    "fuse_evidence",
]
