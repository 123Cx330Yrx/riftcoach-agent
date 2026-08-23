"""Body-free HTTP projections for persisted EvidenceBundle snapshots."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.api.task_models import ApiModel
from app.evidence.fusion import (
    EvidenceBundleDisposition,
    EvidenceClaim,
    EvidenceConfidence,
    PatchVersion,
    Position,
    RoutingRegion,
    SafeIdentifier,
    Sha256Text,
)
from app.evidence.storage import (
    EvidenceSnapshotFreshness,
    EvidenceSnapshotView,
    ProductRunState,
    ProductRunStateValue,
    ProductStateReason,
)
from app.tasks.models import TaskPublicationStatus, TaskStatus


EvidenceFreshnessValue = Literal["current", "stale", "unknown", "expired"]
EvidenceDispositionValue = Literal["complete", "degraded", "rejected"]
EvidenceConfidenceValue = Literal["high", "medium", "low", "unknown"]
EvidenceClaimValue = Literal[
    "riot_match_facts",
    "data_dragon_static",
    "official_patch_facts",
    "current_meta_recommendation",
    "exact_patch_meta_comparison",
]
EvidenceJoinStatusValue = Literal[
    "joined",
    "joined_partial",
    "unjoined",
    "stale",
    "conflict",
]
EvidenceSourceValue = Literal[
    "riot_official",
    "data_dragon",
    "riot_patch",
    "opgg",
]


class EvidenceJoinKeyResponse(ApiModel):
    routing_region: RoutingRegion
    queue_id: int = Field(gt=0, le=10_000)
    position: Position
    champion_name: str = Field(min_length=1, max_length=64)
    patch_version: PatchVersion | None


class EvidenceMatchResponse(ApiModel):
    match_id: SafeIdentifier
    champion_name: str = Field(min_length=1, max_length=64)
    position: Position
    patch_version: PatchVersion | None
    win: bool
    timeline_available: bool


class EvidenceJoinSourcesResponse(ApiModel):
    riot: bool
    data_dragon: bool
    riot_patch: bool
    opgg: bool


class EvidenceJoinResponse(ApiModel):
    key: EvidenceJoinKeyResponse
    status: EvidenceJoinStatusValue
    confidence: EvidenceConfidenceValue
    sources_present: EvidenceJoinSourcesResponse


class EvidenceConflictResponse(ApiModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    sources: list[EvidenceSourceValue] = Field(min_length=2, max_length=4)
    key: EvidenceJoinKeyResponse | None


class EvidenceGapResponse(ApiModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    source: EvidenceSourceValue
    key: EvidenceJoinKeyResponse | None


class RiotOfficialSourceResponse(ApiModel):
    match_count: int = Field(ge=0, le=100)
    digests: list[Sha256Text] = Field(max_length=100)
    freshness: EvidenceFreshnessValue

    @model_validator(mode="after")
    def validate_count(self) -> Self:
        if self.match_count != len(self.digests):
            raise ValueError("Riot match count must match digest count")
        return self


class DataDragonSourceResponse(ApiModel):
    version: PatchVersion | None
    catalog_digest: Sha256Text | None
    freshness: EvidenceFreshnessValue

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if (self.version is None) != (self.catalog_digest is None):
            raise ValueError("Data Dragon identity must be all present or absent")
        return self


class RiotPatchSourceResponse(ApiModel):
    patch_version: PatchVersion | None
    source_digest: Sha256Text | None
    freshness: EvidenceFreshnessValue

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if (self.patch_version is None) != (self.source_digest is None):
            raise ValueError("Riot patch identity must be all present or absent")
        return self


class OpggSourceResponse(ApiModel):
    evidence_count: int = Field(ge=0, le=100)
    digests: list[Sha256Text] = Field(max_length=100)
    provenance: list[Literal["complete", "partial"]] = Field(max_length=100)
    freshness: EvidenceFreshnessValue

    @model_validator(mode="after")
    def validate_count(self) -> Self:
        if self.evidence_count != len(self.digests) or self.evidence_count != len(
            self.provenance
        ):
            raise ValueError("OP.GG count must match digest and provenance counts")
        return self


class EvidenceSourcesResponse(ApiModel):
    riot_official: RiotOfficialSourceResponse
    data_dragon: DataDragonSourceResponse
    riot_patch: RiotPatchSourceResponse
    opgg: OpggSourceResponse


class EvidencePublicProjectionResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    bundle_digest: Sha256Text
    disposition: EvidenceDispositionValue
    confidence: EvidenceConfidenceValue
    claims: list[EvidenceClaimValue]
    matches: list[EvidenceMatchResponse] = Field(max_length=100)
    joins: list[EvidenceJoinResponse] = Field(max_length=100)
    conflicts: list[EvidenceConflictResponse] = Field(max_length=100)
    gaps: list[EvidenceGapResponse] = Field(max_length=100)
    sources: EvidenceSourcesResponse

    @model_validator(mode="after")
    def validate_join_cardinality(self) -> Self:
        if len(self.matches) != len(self.joins):
            raise ValueError("public projection requires one join per match")
        return self


class EvidenceSnapshotResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: UUID
    task_id: UUID
    run_id: str
    revision: int
    bundle_digest: str
    snapshot_digest: str
    stored_at: datetime
    expires_at: datetime | None
    freshness: EvidenceSnapshotFreshness
    bundle_disposition: EvidenceBundleDisposition
    confidence: EvidenceConfidence
    usable_claims: tuple[EvidenceClaim, ...]
    projection: EvidencePublicProjectionResponse

    @classmethod
    def from_view(cls, view: EvidenceSnapshotView) -> "EvidenceSnapshotResponse":
        if not isinstance(view, EvidenceSnapshotView):
            raise TypeError("view must be an EvidenceSnapshotView")
        return cls(
            snapshot_id=view.snapshot_id,
            task_id=view.task_id,
            run_id=view.run_id,
            revision=view.revision,
            bundle_digest=view.bundle_digest,
            snapshot_digest=view.snapshot_digest,
            stored_at=view.stored_at,
            expires_at=view.expires_at,
            freshness=view.freshness,
            bundle_disposition=view.bundle_disposition,
            confidence=view.confidence,
            usable_claims=view.usable_claims,
            projection=EvidencePublicProjectionResponse.model_validate(
                copy.deepcopy(view.projection)
            ),
        )


class ProductStateResponse(ApiModel):
    schema_version: str = "1.0"
    task_id: UUID
    run_id: str
    state: ProductRunStateValue
    reason_code: ProductStateReason
    task_status: TaskStatus
    publication_status: TaskPublicationStatus | None
    report_available: bool
    evidence_revision: int | None = None
    evidence_bundle_digest: str | None = None
    evidence_freshness: EvidenceSnapshotFreshness | None = None
    evidence_disposition: EvidenceBundleDisposition | None = None

    @classmethod
    def from_state(cls, state: ProductRunState) -> "ProductStateResponse":
        if not isinstance(state, ProductRunState):
            raise TypeError("state must be a ProductRunState")
        return cls(**state.model_dump())


__all__ = [
    "EvidencePublicProjectionResponse",
    "EvidenceSnapshotResponse",
    "ProductStateResponse",
]
