from __future__ import annotations

from typing import Protocol

from app.evidence.storage import (
    EvidenceBundleSnapshot,
    EvidenceSnapshotWriteResult,
    PendingEvidenceBundleSnapshot,
)


class EvidenceSnapshotRepositoryError(RuntimeError):
    """Safe repository error; adapters must not expose its original cause."""


class EvidenceSnapshotRepository(Protocol):
    def append(
        self,
        pending: PendingEvidenceBundleSnapshot,
    ) -> EvidenceSnapshotWriteResult: ...

    def get_latest(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> EvidenceBundleSnapshot | None: ...


__all__ = ["EvidenceSnapshotRepository", "EvidenceSnapshotRepositoryError"]
