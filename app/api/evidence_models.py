"""Body-free HTTP projections for persisted EvidenceBundle snapshots."""

from __future__ import annotations

import copy
from datetime import datetime
from uuid import UUID

from app.api.task_models import ApiModel
from app.evidence.fusion import (
    EvidenceBundleDisposition,
    EvidenceClaim,
    EvidenceConfidence,
)
from app.evidence.storage import (
    EvidenceSnapshotFreshness,
    EvidenceSnapshotView,
    ProductRunState,
    ProductRunStateValue,
    ProductStateReason,
)
from app.tasks.models import TaskPublicationStatus, TaskStatus


class EvidenceSnapshotResponse(ApiModel):
    schema_version: str = "1.0"
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
    projection: dict[str, object]

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
            projection=copy.deepcopy(view.projection),
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


__all__ = ["EvidenceSnapshotResponse", "ProductStateResponse"]
