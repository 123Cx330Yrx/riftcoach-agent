"""Backup/restore control-plane contracts for the 8E E4 drill.

The module deliberately stores deletion-marker metadata only. It does not
pretend to be an encrypted backup provider; production backup bytes and KMS
keys remain behind an external adapter.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import UUID

from pydantic import Field, TypeAdapter, ValidationError

from app.harness.run_ids import normalize_run_id
from app.lifecycle.models import (
    LifecycleModel,
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerId,
    SafeCode,
)


BackupErrorCode = Literal[
    "backup_manifest_invalid",
    "restore_erase_replay_failed",
    "restore_compensation_failed",
    "restore_not_ready",
]


class BackupRestoreError(RuntimeError):
    def __init__(self, code: BackupErrorCode) -> None:
        self.code = code
        super().__init__(code)


class BackupDeletionMarker(LifecycleModel):
    marker_id: UUID
    owner_id: OwnerId
    status: OwnerDataDeletionStatus
    marker_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BackupManifest(LifecycleModel):
    schema_version: Literal["1.0"] = "1.0"
    backup_id: SafeCode
    created_at: datetime
    source_schema: SafeCode
    encryption: Literal["external_kms_required"] = "external_kms_required"
    deletion_markers: tuple[BackupDeletionMarker, ...] = Field(max_length=100_000)
    deletion_marker_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RestoreResult:
    backup_id: str
    ready: bool
    replayed_marker_ids: tuple[UUID, ...]


class DeletionMarkerReplayer(Protocol):
    def replay(self, marker: BackupDeletionMarker) -> None: ...

    def rollback(self, marker_ids: tuple[UUID, ...]) -> None: ...


class MarkerReplayDelegate(Protocol):
    def replay(self, marker: BackupDeletionMarker) -> None: ...

    def rollback(self, marker_ids: tuple[UUID, ...]) -> None: ...


@dataclass(frozen=True, slots=True)
class OwnerRunReference:
    """The body-free link from a lifecycle marker to one run data namespace."""

    owner_id: str
    run_id: str
    conversation_id: UUID | None = None
    relationship_id: UUID | None = None

    def __post_init__(self) -> None:
        try:
            TypeAdapter(OwnerId).validate_python(self.owner_id, strict=True)
            normalize_run_id(self.run_id)
        except (TypeError, ValueError, ValidationError):
            raise ValueError("owner_run_reference_invalid") from None
        if self.conversation_id is None and self.relationship_id is None:
            raise ValueError("owner_run_reference_invalid")


class OwnerRunLocator(Protocol):
    def locate(self, marker: OwnerDataDeletionMarker) -> Iterable[OwnerRunReference]: ...


class RunDataCleanup(Protocol):
    def cleanup(self, run_id: str) -> bool: ...


class OwnerRunArtifactTraceCleaner:
    """Remove targeted immutable run directories after SQL visibility is hidden.

    The lifecycle service calls this cleaner only after the PostgreSQL marker is
    committed.  A failed run cleanup raises a body-free error; the marker then
    remains retryable and no online query can expose the hidden records again.
    """

    def __init__(
        self,
        *,
        locator: OwnerRunLocator,
        run_cleaner: RunDataCleanup,
    ) -> None:
        if not callable(getattr(locator, "locate", None)):
            raise TypeError("locator must expose locate()")
        if not callable(getattr(run_cleaner, "cleanup", None)):
            raise TypeError("run_cleaner must expose cleanup()")
        self._locator = locator
        self._run_cleaner = run_cleaner

    def cleanup(self, marker: OwnerDataDeletionMarker) -> None:
        if not isinstance(marker, OwnerDataDeletionMarker):
            raise TypeError("marker must be an OwnerDataDeletionMarker")
        seen: set[str] = set()
        try:
            references = tuple(self._locator.locate(marker))
        except Exception:
            raise RuntimeError("owner_run_reference_invalid") from None
        for reference in references:
            if not isinstance(reference, OwnerRunReference):
                raise RuntimeError("owner_run_reference_invalid")
            if reference.owner_id != marker.owner_id:
                raise RuntimeError("owner_run_reference_invalid")
            if not _reference_matches_marker(reference, marker):
                raise RuntimeError("owner_run_reference_invalid")
            if reference.run_id in seen:
                continue
            seen.add(reference.run_id)
            try:
                cleaned = self._run_cleaner.cleanup(reference.run_id)
            except Exception:
                raise RuntimeError("owner_run_cleanup_failed") from None
            if cleaned is not True:
                raise RuntimeError("owner_run_cleanup_failed")


class IdempotentDeletionMarkerReplayer:
    """Make a restore drill safe to retry within one process."""

    def __init__(self, *, delegate: MarkerReplayDelegate) -> None:
        if not callable(getattr(delegate, "replay", None)):
            raise TypeError("delegate must expose replay()")
        if not callable(getattr(delegate, "rollback", None)):
            raise TypeError("delegate must expose rollback()")
        self._delegate = delegate
        self._applied: set[UUID] = set()
        self._current_replayed: set[UUID] = set()

    def begin_restore(self) -> None:
        """Start a compensation scope for one restore attempt."""

        self._current_replayed.clear()

    def replay(self, marker: BackupDeletionMarker) -> None:
        if marker.marker_id in self._applied:
            return
        self._delegate.replay(marker)
        self._applied.add(marker.marker_id)
        self._current_replayed.add(marker.marker_id)

    def rollback(self, marker_ids: tuple[UUID, ...]) -> None:
        current = tuple(
            marker_id for marker_id in marker_ids if marker_id in self._current_replayed
        )
        if current:
            self._delegate.rollback(current)
            self._applied.difference_update(current)
        self._current_replayed.clear()


def build_backup_manifest(
    *,
    backup_id: str,
    created_at: datetime,
    source_schema: str,
    deletion_markers: tuple[OwnerDataDeletionMarker, ...],
) -> BackupManifest:
    """Create a deterministic metadata manifest without copying private bodies."""

    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise BackupRestoreError("backup_manifest_invalid")
    marker_rows: list[BackupDeletionMarker] = []
    seen_marker_ids: set[UUID] = set()
    for marker in deletion_markers:
        if not isinstance(marker, OwnerDataDeletionMarker):
            raise BackupRestoreError("backup_manifest_invalid")
        if marker.marker_id in seen_marker_ids:
            raise BackupRestoreError("backup_manifest_invalid")
        seen_marker_ids.add(marker.marker_id)
        marker_payload = marker.model_dump(mode="json")
        marker_digest = hashlib.sha256(
            json.dumps(
                marker_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        marker_rows.append(
            BackupDeletionMarker(
                marker_id=marker.marker_id,
                owner_id=marker.owner_id,
                status=marker.status,
                marker_sha256=marker_digest,
            )
        )
    marker_rows.sort(key=lambda row: str(row.marker_id))
    digest = _marker_digest(tuple(marker_rows))
    try:
        return BackupManifest(
            backup_id=backup_id,
            created_at=created_at.astimezone(timezone.utc),
            source_schema=source_schema,
            deletion_markers=tuple(marker_rows),
            deletion_marker_digest=digest,
        )
    except Exception:
        raise BackupRestoreError("backup_manifest_invalid") from None


class BackupRestoreService:
    """Replay deletion markers before exposing a restored system as ready."""

    def __init__(
        self,
        *,
        replayer: DeletionMarkerReplayer,
        ready_probe: Callable[[], bool] | None = None,
    ) -> None:
        if not callable(getattr(replayer, "replay", None)):
            raise TypeError("replayer must expose replay()")
        if not callable(getattr(replayer, "rollback", None)):
            raise TypeError("replayer must expose rollback()")
        if ready_probe is not None and not callable(ready_probe):
            raise TypeError("ready_probe must be callable")
        self._replayer = replayer
        self._ready_probe = ready_probe or (lambda: True)

    def restore(self, manifest: BackupManifest) -> RestoreResult:
        if not isinstance(manifest, BackupManifest):
            raise BackupRestoreError("backup_manifest_invalid")
        if manifest.deletion_marker_digest != _marker_digest(manifest.deletion_markers):
            raise BackupRestoreError("backup_manifest_invalid")
        begin_restore = getattr(self._replayer, "begin_restore", None)
        if callable(begin_restore):
            begin_restore()
        replayed: list[UUID] = []
        try:
            for marker in manifest.deletion_markers:
                self._replayer.replay(marker)
                replayed.append(marker.marker_id)
            if not self._ready_probe():
                raise BackupRestoreError("restore_not_ready")
        except BackupRestoreError:
            self._rollback(tuple(replayed))
            raise
        except Exception:
            self._rollback(tuple(replayed))
            raise BackupRestoreError("restore_erase_replay_failed") from None
        return RestoreResult(
            backup_id=manifest.backup_id,
            ready=True,
            replayed_marker_ids=tuple(replayed),
        )

    def _rollback(self, marker_ids: tuple[UUID, ...]) -> None:
        if not marker_ids:
            return
        try:
            self._replayer.rollback(marker_ids)
        except Exception:
            raise BackupRestoreError("restore_compensation_failed") from None


def _marker_digest(markers: tuple[BackupDeletionMarker, ...]) -> str:
    ordered = tuple(sorted(markers, key=lambda row: str(row.marker_id)))
    return hashlib.sha256(
        "\n".join(row.marker_sha256 for row in ordered).encode("ascii")
    ).hexdigest()


def _reference_matches_marker(
    reference: OwnerRunReference,
    marker: OwnerDataDeletionMarker,
) -> bool:
    if marker.scope in {
        OwnerDataDeleteScope.CONVERSATION_ONLY,
        OwnerDataDeleteScope.CONVERSATION_AND_DERIVED_MEMORY,
    }:
        return (
            marker.conversation_id is not None
            and reference.conversation_id == marker.conversation_id
        )
    return (
        marker.relationship_id is not None
        and reference.relationship_id == marker.relationship_id
    )


__all__ = [
    "BackupDeletionMarker",
    "BackupManifest",
    "BackupRestoreError",
    "BackupRestoreService",
    "DeletionMarkerReplayer",
    "IdempotentDeletionMarkerReplayer",
    "OwnerRunArtifactTraceCleaner",
    "OwnerRunLocator",
    "OwnerRunReference",
    "RunDataCleanup",
    "RestoreResult",
    "build_backup_manifest",
]
