"""Typed, provenance-aware evidence fusion primitives."""

from .adapters import (
    EvidenceAdapterError,
    data_dragon_snapshot_from_identity,
    riot_match_from_summary_row,
)

from .fusion import (
    DataDragonSnapshot,
    EvidenceBundle,
    EvidenceBundleDisposition,
    EvidenceClaim,
    EvidenceConfidence,
    EvidenceConflict,
    EvidenceFreshness,
    EvidenceGap,
    EvidenceJoin,
    EvidenceJoinKey,
    EvidenceJoinStatus,
    EvidenceSource,
    OfficialPatchEvidence,
    RiotMatchEvidence,
    fuse_evidence,
)

__all__ = [
    "DataDragonSnapshot",
    "EvidenceAdapterError",
    "EvidenceBundle",
    "EvidenceBundleDisposition",
    "EvidenceClaim",
    "EvidenceConfidence",
    "EvidenceConflict",
    "EvidenceFreshness",
    "EvidenceGap",
    "EvidenceJoin",
    "EvidenceJoinKey",
    "EvidenceJoinStatus",
    "EvidenceSource",
    "OfficialPatchEvidence",
    "RiotMatchEvidence",
    "fuse_evidence",
    "data_dragon_snapshot_from_identity",
    "riot_match_from_summary_row",
]
