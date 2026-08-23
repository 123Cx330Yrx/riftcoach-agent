"""Immutable EvidenceBundle persistence and product-state contracts.

This module contains no database or network I/O.  It defines the strict wire
shape stored by the PostgreSQL adapter and the pure projections consumed by
the API and, later, the frontend.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal, Mapping, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.evidence.fusion import (
    DataDragonSnapshot,
    EvidenceBundle,
    EvidenceBundleDisposition,
    EvidenceClaim,
    EvidenceConfidence,
    EvidenceConflict,
    EvidenceGap,
    EvidenceJoin,
    OfficialPatchEvidence,
    RiotMatchEvidence,
)
from app.harness.run_ids import normalize_run_id
from app.meta.models import (
    LaneMetaChampionFact,
    MetaEvidence,
    MetaProvenance,
    MetaUseCase,
)
from app.tasks.models import (
    OwnerId,
    ReviewTaskView,
    TaskPublicationStatus,
    TaskStatus,
)


_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_REFRESH_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "riot_matches",
        "data_dragon",
        "official_patch",
        "meta_evidence",
        "joins",
        "conflicts",
        "gaps",
        "claims",
        "disposition",
        "confidence",
        "created_at",
        "digest",
    }
)
_META_KEYS = frozenset(
    {
        "source",
        "remote_tool",
        "position",
        "facts",
        "provenance",
        "upstream_patch",
        "source_generated_at",
        "retrieved_at",
        "expires_at",
        "allowed_uses",
        "catalog_digest",
        "tool_schema_digest",
        "digest",
    }
)


class EvidenceStorageModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class EvidenceSnapshotFreshness(StrEnum):
    CURRENT = "current"
    EXPIRED = "expired"


class EvidenceSnapshotWriteDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"


class ProductRunStateValue(StrEnum):
    PUBLISHED = "published"
    DEGRADED = "degraded"
    REJECTED = "rejected"
    NOT_READY = "not_ready"


class ProductStateReason(StrEnum):
    READY = "ready"
    TASK_PENDING = "task_pending"
    RECOVERY_REQUIRED = "recovery_required"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    QUALITY_REJECTED = "quality_rejected"
    QUALITY_DEGRADED = "quality_degraded"
    EVIDENCE_NOT_AVAILABLE = "evidence_not_available"
    EVIDENCE_EXPIRED = "evidence_expired"
    EVIDENCE_DEGRADED = "evidence_degraded"
    EVIDENCE_REJECTED = "evidence_rejected"


class EvidenceBundleSnapshot(EvidenceStorageModel):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: UUID
    task_id: UUID
    run_id: str
    owner_id: OwnerId
    revision: int = Field(ge=1)
    refresh_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_REFRESH_PATTERN,
    )
    bundle: EvidenceBundle
    stored_at: datetime
    expires_at: datetime | None
    snapshot_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=_DIGEST_PATTERN,
    )

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("stored_at", "expires_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if not self.bundle.has_valid_digest():
            raise ValueError("evidence bundle digest is invalid")
        if self.expires_at != derive_bundle_expiry(self.bundle):
            raise ValueError("snapshot expiry must match its typed evidence")
        if not self.has_valid_digest():
            raise ValueError("snapshot digest is invalid")
        return self

    @classmethod
    def create(
        cls,
        *,
        snapshot_id: UUID,
        task_id: UUID,
        run_id: str,
        owner_id: str,
        revision: int,
        refresh_id: str,
        bundle: EvidenceBundle,
        stored_at: datetime,
    ) -> "EvidenceBundleSnapshot":
        expires_at = derive_bundle_expiry(bundle)
        normalized_stored_at = _as_utc(stored_at)
        digest = _snapshot_digest(
            snapshot_id=snapshot_id,
            task_id=task_id,
            run_id=run_id,
            owner_id=owner_id,
            revision=revision,
            refresh_id=refresh_id,
            bundle_digest=bundle.digest,
            stored_at=normalized_stored_at,
            expires_at=expires_at,
        )
        return cls(
            snapshot_id=snapshot_id,
            task_id=task_id,
            run_id=run_id,
            owner_id=owner_id,
            revision=revision,
            refresh_id=refresh_id,
            bundle=bundle,
            stored_at=normalized_stored_at,
            expires_at=expires_at,
            snapshot_digest=digest,
        )

    def computed_digest(self) -> str:
        return _snapshot_digest(
            snapshot_id=self.snapshot_id,
            task_id=self.task_id,
            run_id=self.run_id,
            owner_id=self.owner_id,
            revision=self.revision,
            refresh_id=self.refresh_id,
            bundle_digest=self.bundle.digest,
            stored_at=self.stored_at,
            expires_at=self.expires_at,
        )

    def has_valid_digest(self) -> bool:
        return self.snapshot_digest == self.computed_digest()


class PendingEvidenceBundleSnapshot(EvidenceStorageModel):
    task_id: UUID
    run_id: str
    owner_id: OwnerId
    refresh_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_REFRESH_PATTERN,
    )
    bundle: EvidenceBundle
    stored_at: datetime

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("stored_at")
    @classmethod
    def normalize_stored_at(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        if not self.bundle.has_valid_digest():
            raise ValueError("pending evidence bundle digest is invalid")
        return self


class EvidenceSnapshotWriteResult(EvidenceStorageModel):
    disposition: EvidenceSnapshotWriteDisposition
    snapshot: EvidenceBundleSnapshot


class EvidenceSnapshotView(EvidenceStorageModel):
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
    projection: dict[str, Any]


class ProductRunState(EvidenceStorageModel):
    schema_version: Literal["1.0"] = "1.0"
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


def bundle_to_storage_projection(bundle: EvidenceBundle) -> dict[str, object]:
    if not isinstance(bundle, EvidenceBundle) or not bundle.has_valid_digest():
        raise ValueError("bundle must be a valid EvidenceBundle")
    projection = bundle.to_storage_projection()
    # Force a JSON-compatible deep copy at the boundary and reject non-finite
    # floats before an adapter can hand the value to JSONB.
    return json.loads(
        json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


def bundle_from_storage_projection(value: Mapping[str, Any]) -> EvidenceBundle:
    if not isinstance(value, Mapping) or frozenset(value) != _TOP_LEVEL_KEYS:
        raise ValueError("evidence storage projection shape is invalid")
    payload = copy.deepcopy(dict(value))
    expected_digest = payload.pop("digest", None)
    if not isinstance(expected_digest, str):
        raise ValueError("evidence storage projection digest is invalid")
    try:
        meta_rows = payload["meta_evidence"]
        if not isinstance(meta_rows, list):
            raise ValueError("meta evidence storage shape is invalid")
        meta_evidence = tuple(_meta_from_storage(row) for row in meta_rows)
        result = EvidenceBundle(
            schema_version=payload["schema_version"],
            riot_matches=tuple(
                _model_from_json(RiotMatchEvidence, row)
                for row in _list(payload["riot_matches"])
            ),
            data_dragon=(
                None
                if payload["data_dragon"] is None
                else _model_from_json(DataDragonSnapshot, payload["data_dragon"])
            ),
            official_patch=(
                None
                if payload["official_patch"] is None
                else _model_from_json(
                    OfficialPatchEvidence,
                    payload["official_patch"],
                )
            ),
            meta_evidence=meta_evidence,
            joins=tuple(
                _model_from_json(EvidenceJoin, row)
                for row in _list(payload["joins"])
            ),
            conflicts=tuple(
                _model_from_json(EvidenceConflict, row)
                for row in _list(payload["conflicts"])
            ),
            gaps=tuple(
                _model_from_json(EvidenceGap, row)
                for row in _list(payload["gaps"])
            ),
            claims=tuple(EvidenceClaim(item) for item in _list(payload["claims"])),
            disposition=EvidenceBundleDisposition(payload["disposition"]),
            confidence=EvidenceConfidence(payload["confidence"]),
            created_at=_datetime(payload["created_at"]),
            digest=expected_digest,
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("evidence storage projection is invalid") from None
    if result.digest != expected_digest or not result.has_valid_digest():
        raise ValueError("evidence storage projection digest mismatch")
    return result


def derive_bundle_expiry(bundle: EvidenceBundle) -> datetime | None:
    if not isinstance(bundle, EvidenceBundle):
        raise TypeError("bundle must be an EvidenceBundle")
    values = [row.expires_at for row in bundle.meta_evidence]
    if bundle.official_patch is not None and bundle.official_patch.expires_at is not None:
        values.append(bundle.official_patch.expires_at)
    return None if not values else min(values)


def project_evidence_snapshot(
    snapshot: EvidenceBundleSnapshot,
    *,
    now: datetime,
) -> EvidenceSnapshotView:
    if not isinstance(snapshot, EvidenceBundleSnapshot) or not snapshot.has_valid_digest():
        raise ValueError("snapshot must have a valid identity")
    checked_at = _as_utc(now)
    expired = snapshot.expires_at is not None and checked_at >= snapshot.expires_at
    freshness = (
        EvidenceSnapshotFreshness.EXPIRED
        if expired
        else EvidenceSnapshotFreshness.CURRENT
    )
    claims = tuple(
        claim
        for claim in snapshot.bundle.claims
        if not expired
        or claim
        not in {
            EvidenceClaim.CURRENT_META_RECOMMENDATION,
            EvidenceClaim.EXACT_PATCH_META_COMPARISON,
        }
    )
    projection = copy.deepcopy(snapshot.bundle.to_public_projection())
    if expired:
        projection["claims"] = sorted(item.value for item in claims)
        sources = projection.get("sources")
        if isinstance(sources, dict):
            for source_name in ("opgg", "riot_patch"):
                row = sources.get(source_name)
                if isinstance(row, dict):
                    row["freshness"] = EvidenceSnapshotFreshness.EXPIRED.value
    return EvidenceSnapshotView(
        snapshot_id=snapshot.snapshot_id,
        task_id=snapshot.task_id,
        run_id=snapshot.run_id,
        revision=snapshot.revision,
        bundle_digest=snapshot.bundle.digest,
        snapshot_digest=snapshot.snapshot_digest,
        stored_at=snapshot.stored_at,
        expires_at=snapshot.expires_at,
        freshness=freshness,
        bundle_disposition=snapshot.bundle.disposition,
        confidence=snapshot.bundle.confidence,
        usable_claims=claims,
        projection=projection,
    )


def project_product_run_state(
    task: ReviewTaskView,
    snapshot: EvidenceBundleSnapshot | None,
    *,
    now: datetime,
) -> ProductRunState:
    if not isinstance(task, ReviewTaskView):
        raise TypeError("task must be a ReviewTaskView")
    if snapshot is not None and (
        snapshot.task_id != task.task_id or snapshot.run_id != task.run_id
    ):
        raise ValueError("snapshot identity must match the task")
    view = None if snapshot is None else project_evidence_snapshot(snapshot, now=now)

    if task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
        state, reason = ProductRunStateValue.NOT_READY, ProductStateReason.TASK_PENDING
    elif task.status is TaskStatus.RECOVERY_REQUIRED:
        state, reason = (
            ProductRunStateValue.NOT_READY,
            ProductStateReason.RECOVERY_REQUIRED,
        )
    elif task.status is TaskStatus.FAILED:
        state, reason = ProductRunStateValue.REJECTED, ProductStateReason.TASK_FAILED
    elif task.status is TaskStatus.CANCELLED:
        state, reason = (
            ProductRunStateValue.REJECTED,
            ProductStateReason.TASK_CANCELLED,
        )
    elif task.publication_status is TaskPublicationStatus.REJECTED:
        state, reason = (
            ProductRunStateValue.REJECTED,
            ProductStateReason.QUALITY_REJECTED,
        )
    elif task.publication_status is TaskPublicationStatus.DEGRADED:
        state, reason = (
            ProductRunStateValue.DEGRADED,
            ProductStateReason.QUALITY_DEGRADED,
        )
    elif view is None:
        state, reason = (
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_NOT_AVAILABLE,
        )
    elif view.freshness is EvidenceSnapshotFreshness.EXPIRED:
        state, reason = (
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_EXPIRED,
        )
    elif view.bundle_disposition is EvidenceBundleDisposition.COMPLETE:
        state, reason = ProductRunStateValue.PUBLISHED, ProductStateReason.READY
    elif view.bundle_disposition is EvidenceBundleDisposition.REJECTED:
        state, reason = (
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_REJECTED,
        )
    else:
        state, reason = (
            ProductRunStateValue.DEGRADED,
            ProductStateReason.EVIDENCE_DEGRADED,
        )

    return ProductRunState(
        task_id=task.task_id,
        run_id=task.run_id,
        state=state,
        reason_code=reason,
        task_status=task.status,
        publication_status=task.publication_status,
        report_available=task.report_available,
        evidence_revision=None if view is None else view.revision,
        evidence_bundle_digest=None if view is None else view.bundle_digest,
        evidence_freshness=None if view is None else view.freshness,
        evidence_disposition=None if view is None else view.bundle_disposition,
    )


def _meta_from_storage(value: Any) -> MetaEvidence:
    if not isinstance(value, Mapping) or frozenset(value) != _META_KEYS:
        raise ValueError("meta evidence storage shape is invalid")
    expected_digest = value.get("digest")
    facts_value = value.get("facts")
    if not isinstance(facts_value, list):
        raise ValueError("meta facts storage shape is invalid")
    meta = MetaEvidence(
        source=value.get("source"),
        remote_tool=value.get("remote_tool"),
        position=value.get("position"),
        facts=tuple(
            LaneMetaChampionFact(**_mapping(row))
            for row in facts_value
        ),
        provenance=MetaProvenance(value.get("provenance")),
        upstream_patch=value.get("upstream_patch"),
        source_generated_at=(
            None
            if value.get("source_generated_at") is None
            else _datetime(value.get("source_generated_at"))
        ),
        retrieved_at=_datetime(value.get("retrieved_at")),
        expires_at=_datetime(value.get("expires_at")),
        allowed_uses=frozenset(
            MetaUseCase(item) for item in _list(value.get("allowed_uses"))
        ),
        catalog_digest=value.get("catalog_digest"),
        tool_schema_digest=value.get("tool_schema_digest"),
    )
    if meta.digest != expected_digest:
        raise ValueError("meta evidence digest mismatch")
    return meta


def _model_from_json(model_type, value):
    return model_type.model_validate_json(
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    )


def _list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError("storage value must be a list")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("storage value must be an object")
    return dict(value)


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("storage timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("storage timestamp is invalid") from None
    return _as_utc(parsed)


def _snapshot_digest(
    *,
    snapshot_id: UUID,
    task_id: UUID,
    run_id: str,
    owner_id: str,
    revision: int,
    refresh_id: str,
    bundle_digest: str,
    stored_at: datetime,
    expires_at: datetime | None,
) -> str:
    components = (
        "1.0",
        str(snapshot_id),
        str(task_id),
        normalize_run_id(run_id),
        owner_id,
        str(revision),
        refresh_id,
        bundle_digest,
        _timestamp(stored_at),
        "" if expires_at is None else _timestamp(expires_at),
    )
    return hashlib.sha256("\x1f".join(components).encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("evidence timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


__all__ = [
    "EvidenceBundleSnapshot",
    "EvidenceSnapshotFreshness",
    "EvidenceSnapshotView",
    "EvidenceSnapshotWriteDisposition",
    "EvidenceSnapshotWriteResult",
    "PendingEvidenceBundleSnapshot",
    "ProductRunState",
    "ProductRunStateValue",
    "ProductStateReason",
    "bundle_from_storage_projection",
    "bundle_to_storage_projection",
    "derive_bundle_expiry",
    "project_evidence_snapshot",
    "project_product_run_state",
]
