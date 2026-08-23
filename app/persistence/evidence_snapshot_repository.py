from __future__ import annotations

import copy
import json
from uuid import uuid4

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.evidence.ports import EvidenceSnapshotRepositoryError
from app.evidence.storage import (
    EvidenceBundleSnapshot,
    EvidenceSnapshotWriteDisposition,
    EvidenceSnapshotWriteResult,
    PendingEvidenceBundleSnapshot,
    bundle_from_storage_projection,
    bundle_to_storage_projection,
)
from app.harness.run_ids import normalize_run_id
from app.persistence.evidence_snapshot_record import EvidenceBundleSnapshotRecord
from app.persistence.task_record import ReviewTaskRecord
from app.tasks.models import TaskStatus


_MAX_PAYLOAD_BYTES = 262_144
_WRITABLE_STATUSES = frozenset(
    {TaskStatus.RUNNING.value, TaskStatus.SUCCEEDED.value}
)


class PostgresEvidenceSnapshotRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        snapshot_id_factory=uuid4,
    ) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        if not callable(snapshot_id_factory):
            raise TypeError("snapshot_id_factory must be callable")
        self._session_factory = session_factory
        self._snapshot_id_factory = snapshot_id_factory

    def append(
        self,
        pending: PendingEvidenceBundleSnapshot,
    ) -> EvidenceSnapshotWriteResult:
        if not isinstance(pending, PendingEvidenceBundleSnapshot):
            raise TypeError("pending must be a PendingEvidenceBundleSnapshot")
        payload = bundle_to_storage_projection(pending.bundle)
        if _payload_size(payload) > _MAX_PAYLOAD_BYTES:
            raise EvidenceSnapshotRepositoryError("evidence_snapshot_too_large")
        try:
            with self._session_factory() as session:
                with session.begin():
                    task = session.scalar(
                        sa.select(ReviewTaskRecord)
                        .where(
                            ReviewTaskRecord.task_id == pending.task_id,
                            ReviewTaskRecord.run_id == pending.run_id,
                            ReviewTaskRecord.owner_id == pending.owner_id,
                        )
                        .with_for_update()
                    )
                    if task is None:
                        raise EvidenceSnapshotRepositoryError(
                            "evidence_task_not_found"
                        )
                    if task.status not in _WRITABLE_STATUSES:
                        raise EvidenceSnapshotRepositoryError(
                            "evidence_task_not_writable"
                        )
                    if pending.stored_at < task.created_at:
                        raise EvidenceSnapshotRepositoryError(
                            "evidence_snapshot_time_invalid"
                        )

                    existing = session.scalar(
                        sa.select(EvidenceBundleSnapshotRecord).where(
                            EvidenceBundleSnapshotRecord.task_id == pending.task_id,
                            EvidenceBundleSnapshotRecord.refresh_id
                            == pending.refresh_id,
                        )
                    )
                    if existing is not None:
                        snapshot = _record_to_snapshot(existing)
                        # ``stored_at`` belongs to the first committed snapshot,
                        # not to a client's retry attempt.  Refresh idempotency is
                        # therefore content-based: the same validated bundle
                        # replays even when the retry happens later.
                        if pending.bundle.digest != snapshot.bundle.digest:
                            raise EvidenceSnapshotRepositoryError(
                                "evidence_snapshot_conflict"
                            )
                        return EvidenceSnapshotWriteResult(
                            disposition=EvidenceSnapshotWriteDisposition.REPLAYED,
                            snapshot=snapshot,
                        )

                    latest_revision = session.scalar(
                        sa.select(sa.func.max(EvidenceBundleSnapshotRecord.revision))
                        .where(
                            EvidenceBundleSnapshotRecord.task_id == pending.task_id
                        )
                    )
                    revision = int(latest_revision or 0) + 1
                    snapshot = EvidenceBundleSnapshot.create(
                        snapshot_id=self._snapshot_id_factory(),
                        task_id=pending.task_id,
                        run_id=pending.run_id,
                        owner_id=pending.owner_id,
                        revision=revision,
                        refresh_id=pending.refresh_id,
                        bundle=pending.bundle,
                        stored_at=pending.stored_at,
                    )
                    session.add(
                        EvidenceBundleSnapshotRecord(
                            snapshot_id=snapshot.snapshot_id,
                            task_id=snapshot.task_id,
                            run_id=snapshot.run_id,
                            owner_id=snapshot.owner_id,
                            revision=snapshot.revision,
                            refresh_id=snapshot.refresh_id,
                            bundle_digest=snapshot.bundle.digest,
                            snapshot_digest=snapshot.snapshot_digest,
                            payload=copy.deepcopy(payload),
                            stored_at=snapshot.stored_at,
                            expires_at=snapshot.expires_at,
                        )
                    )
                    session.flush()
                    return EvidenceSnapshotWriteResult(
                        disposition=EvidenceSnapshotWriteDisposition.CREATED,
                        snapshot=snapshot,
                    )
        except EvidenceSnapshotRepositoryError:
            raise
        except SQLAlchemyError:
            raise EvidenceSnapshotRepositoryError(
                "evidence_snapshot_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise EvidenceSnapshotRepositoryError(
                "evidence_snapshot_integrity_failed"
            ) from None

    def get_latest(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> EvidenceBundleSnapshot | None:
        if not isinstance(owner_id, str) or not owner_id:
            raise TypeError("owner_id must be a non-empty string")
        normalized_run_id = normalize_run_id(run_id)
        try:
            with self._session_factory() as session:
                with session.begin():
                    record = session.scalar(
                        sa.select(EvidenceBundleSnapshotRecord)
                        .where(
                            EvidenceBundleSnapshotRecord.owner_id == owner_id,
                            EvidenceBundleSnapshotRecord.run_id == normalized_run_id,
                        )
                        .order_by(
                            EvidenceBundleSnapshotRecord.revision.desc()
                        )
                        .limit(1)
                    )
                    return None if record is None else _record_to_snapshot(record)
        except EvidenceSnapshotRepositoryError:
            raise
        except SQLAlchemyError:
            raise EvidenceSnapshotRepositoryError(
                "evidence_snapshot_unavailable"
            ) from None
        except (TypeError, ValueError, ValidationError):
            raise EvidenceSnapshotRepositoryError(
                "evidence_snapshot_integrity_failed"
            ) from None


def _record_to_snapshot(
    record: EvidenceBundleSnapshotRecord,
) -> EvidenceBundleSnapshot:
    payload = record.payload
    if hasattr(payload, "obj"):
        payload = payload.obj
    bundle = bundle_from_storage_projection(payload)
    if bundle.digest != record.bundle_digest:
        raise EvidenceSnapshotRepositoryError(
            "evidence_snapshot_integrity_failed"
        )
    try:
        return EvidenceBundleSnapshot(
            snapshot_id=record.snapshot_id,
            task_id=record.task_id,
            run_id=record.run_id,
            owner_id=record.owner_id,
            revision=record.revision,
            refresh_id=record.refresh_id,
            bundle=bundle,
            stored_at=record.stored_at,
            expires_at=record.expires_at,
            snapshot_digest=record.snapshot_digest,
        )
    except (TypeError, ValueError, ValidationError):
        raise EvidenceSnapshotRepositoryError(
            "evidence_snapshot_integrity_failed"
        ) from None


def _payload_size(payload: dict[str, object]) -> int:
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


__all__ = ["PostgresEvidenceSnapshotRepository"]
