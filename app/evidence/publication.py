"""Offline files-ready contracts, not database publication authorization."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.harness.run_ids import normalize_run_id
from app.memory.context_models import OwnerId
from app.meta.models import MetaEvidence
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.product.run_receipts import RunReceiptReference
from .fusion import DataDragonSnapshot, OfficialPatchEvidence
from .summary_bridge import SummaryEvidenceProjection, summary_to_evidence

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class EvidencePublicationIntegrityError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("evidence_publication_integrity_failed")


class PublicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                             revalidate_instances="always")


class EvidencePublicationContext(PublicationModel):
    owner_id: OwnerId
    task_id: UUID
    run_id: str
    request_fingerprint: Digest
    mode: Literal["evidence_bound_v1"] = "evidence_bound_v1"

    @field_validator("run_id")
    @classmethod
    def valid_run(cls, value: str) -> str:
        if normalize_run_id(value) != value:
            raise ValueError("run_id must be normalized")
        return value


@dataclass(frozen=True)
class EvidencePublicationSources:
    """Already materialized sources; construction and projection do no I/O."""
    now: datetime
    observed_at: datetime | None = None
    data_dragon: DataDragonSnapshot | None = None
    official_patch: OfficialPatchEvidence | None = None
    meta_evidence: tuple[MetaEvidence, ...] = ()

    def project(self, summary: dict, *, routing_region: str) -> SummaryEvidenceProjection:
        return summary_to_evidence(
            summary, routing_region=routing_region, now=self.now,
            observed_at=self.observed_at, data_dragon=self.data_dragon,
            official_patch=self.official_patch, meta_evidence=self.meta_evidence,
        )


class EvidenceBundleReference(PublicationModel):
    relative_path: Literal["evidence_bundle.json"] = "evidence_bundle.json"
    sha256: Digest
    bundle_digest: Digest


class EvidencePublicationManifest(PublicationModel):
    schema_version: Literal["1.0"] = "1.0"
    state: Literal["files_ready"] = "files_ready"
    context: EvidencePublicationContext
    summary_digest: Digest
    digest_scope: Literal["summary_projection"] = "summary_projection"
    observation_basis: Literal["summary_generated_at", "caller_observed_at"]
    bundle: EvidenceBundleReference
    summary: RuntimeArtifactReference
    receipt: RunReceiptReference
    trace: RuntimeTraceReference
    report: RuntimeArtifactReference | None = None

    @model_validator(mode="after")
    def identities(self) -> EvidencePublicationManifest:
        if self.receipt.run_id != self.context.run_id or self.trace.run_id != self.context.run_id:
            raise ValueError("publication run identity mismatch")
        if (self.summary.kind != "player_summary"
                or self.summary.relative_path != "inputs/player_summary.json"
                or self.summary.producer != "review_harness.input"
                or self.summary.schema_version != "1.0"):
            raise ValueError("publication summary identity mismatch")
        if self.report is not None and self.report.kind != "final_report":
            raise ValueError("publication report identity mismatch")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.model_dump(mode="json"))

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes())


class EvidencePublicationWriter(Protocol):
    def write(self, context: EvidencePublicationContext,
              projection: SummaryEvidenceProjection) -> EvidencePublicationManifest: ...
