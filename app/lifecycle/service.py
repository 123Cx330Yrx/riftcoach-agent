from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, Protocol, TypeAlias
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.lifecycle.models import (
    OwnerDataDeleteCommand,
    OwnerDataDeletionMarker,
    OwnerDataDeletionStatus,
    OwnerDataExport,
    OwnerDataPurgeSummary,
    OwnerDataRetentionSummary,
    OwnerId,
)


LifecycleErrorCode: TypeAlias = Literal[
    "deletion_not_found",
    "idempotency_conflict",
    "export_too_large",
    "lifecycle_unavailable",
    "lifecycle_integrity_failed",
]
_ERROR_CODES = frozenset(
    {
        "deletion_not_found",
        "idempotency_conflict",
        "export_too_large",
        "lifecycle_unavailable",
        "lifecycle_integrity_failed",
    }
)
Clock = Callable[[], datetime]
_OWNER_ADAPTER = TypeAdapter(OwnerId)


class OwnerDataLifecycleRepository(Protocol):
    def export_owner_data(
        self,
        *,
        owner_id: str,
        generated_at: datetime,
        limit_per_section: int,
    ) -> OwnerDataExport: ...

    def hide_owner_data(
        self, command: OwnerDataDeleteCommand
    ) -> OwnerDataDeletionMarker: ...

    def get_deletion_marker(
        self, *, owner_id: str, marker_id: UUID
    ) -> OwnerDataDeletionMarker | None: ...

    def complete_deletion(
        self, *, owner_id: str, marker_id: UUID, completed_at: datetime
    ) -> OwnerDataDeletionMarker: ...

    def mark_cleanup_failed(
        self,
        *,
        owner_id: str,
        marker_id: UUID,
        safe_reason: str,
        updated_at: datetime,
    ) -> OwnerDataDeletionMarker: ...

    def apply_retention(
        self, *, evaluated_at: datetime, batch_size: int
    ) -> OwnerDataRetentionSummary: ...

    def purge_hidden(
        self, *, evaluated_at: datetime, batch_size: int
    ) -> OwnerDataPurgeSummary: ...


class OwnerDataCleanupPort(Protocol):
    def cleanup(self, marker: OwnerDataDeletionMarker) -> None: ...


class OwnerDataLifecycleError(RuntimeError):
    def __init__(self, code: LifecycleErrorCode) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported lifecycle error code")
        self.code = code
        super().__init__(code)


class NoopOwnerDataCleaner:
    """V1 has no owner-wide file body beyond independently managed run data."""

    def cleanup(self, marker: OwnerDataDeletionMarker) -> None:
        if not isinstance(marker, OwnerDataDeletionMarker):
            raise TypeError("marker must be an OwnerDataDeletionMarker")


class OwnerDataLifecycleService:
    def __init__(
        self,
        *,
        repository: OwnerDataLifecycleRepository,
        cleaner: OwnerDataCleanupPort,
        clock: Clock | None = None,
        export_limit_per_section: int = 500,
    ) -> None:
        for method_name in (
            "export_owner_data",
            "hide_owner_data",
            "get_deletion_marker",
            "complete_deletion",
            "mark_cleanup_failed",
            "apply_retention",
            "purge_hidden",
        ):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(getattr(cleaner, "cleanup", None)):
            raise TypeError("cleaner must expose cleanup()")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        if type(export_limit_per_section) is not int or not 1 <= export_limit_per_section <= 500:
            raise TypeError("export_limit_per_section must be an integer from 1 to 500")
        self._repository = repository
        self._cleaner = cleaner
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._export_limit = export_limit_per_section

    def export(self, *, owner_id: str) -> OwnerDataExport:
        normalized_owner = _owner(owner_id)
        try:
            result = self._repository.export_owner_data(
                owner_id=normalized_owner,
                generated_at=self._now(),
                limit_per_section=self._export_limit,
            )
        except OwnerDataLifecycleError:
            raise
        except Exception:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        if not isinstance(result, OwnerDataExport) or result.owner_id != normalized_owner:
            raise OwnerDataLifecycleError("lifecycle_integrity_failed")
        return result

    def delete(self, command: OwnerDataDeleteCommand) -> OwnerDataDeletionMarker:
        if not isinstance(command, OwnerDataDeleteCommand):
            raise TypeError("command must be an OwnerDataDeleteCommand")
        try:
            marker = self._repository.hide_owner_data(command)
        except OwnerDataLifecycleError:
            raise
        except Exception:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        return self._finish_cleanup(marker)

    def retry(self, *, owner_id: str, marker_id: UUID) -> OwnerDataDeletionMarker:
        normalized_owner = _owner(owner_id)
        if not isinstance(marker_id, UUID):
            raise TypeError("marker_id must be a UUID")
        try:
            marker = self._repository.get_deletion_marker(
                owner_id=normalized_owner,
                marker_id=marker_id,
            )
        except Exception:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        if marker is None:
            raise OwnerDataLifecycleError("deletion_not_found")
        return self._finish_cleanup(marker)

    def apply_retention(self, *, batch_size: int = 100) -> OwnerDataRetentionSummary:
        size = _batch_size(batch_size)
        try:
            result = self._repository.apply_retention(
                evaluated_at=self._now(), batch_size=size
            )
        except Exception:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        if not isinstance(result, OwnerDataRetentionSummary):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed")
        return result

    def purge(self, *, batch_size: int = 100) -> OwnerDataPurgeSummary:
        size = _batch_size(batch_size)
        try:
            result = self._repository.purge_hidden(
                evaluated_at=self._now(), batch_size=size
            )
        except Exception:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        if not isinstance(result, OwnerDataPurgeSummary):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed")
        return result

    def _finish_cleanup(
        self, marker: OwnerDataDeletionMarker
    ) -> OwnerDataDeletionMarker:
        if not isinstance(marker, OwnerDataDeletionMarker):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed")
        if marker.status is OwnerDataDeletionStatus.COMPLETE:
            return marker
        try:
            self._cleaner.cleanup(marker)
        except Exception:
            try:
                failed = self._repository.mark_cleanup_failed(
                    owner_id=marker.owner_id,
                    marker_id=marker.marker_id,
                    safe_reason="cleanup_failed",
                    updated_at=self._now(),
                )
            except Exception:
                return marker
            if not isinstance(failed, OwnerDataDeletionMarker):
                return marker
            return failed
        try:
            completed = self._repository.complete_deletion(
                owner_id=marker.owner_id,
                marker_id=marker.marker_id,
                completed_at=self._now(),
            )
        except Exception:
            raise OwnerDataLifecycleError("lifecycle_unavailable") from None
        if not isinstance(completed, OwnerDataDeletionMarker):
            raise OwnerDataLifecycleError("lifecycle_integrity_failed")
        return completed

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise OwnerDataLifecycleError("lifecycle_integrity_failed")
        return value.astimezone(timezone.utc)


def _owner(value: str) -> str:
    try:
        return _OWNER_ADAPTER.validate_python(value, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TypeError("owner_id must be a bounded safe identifier") from None


def _batch_size(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 1_000:
        raise TypeError("batch_size must be an integer from 1 to 1000")
    return value


__all__ = [
    "NoopOwnerDataCleaner",
    "OwnerDataCleanupPort",
    "OwnerDataLifecycleError",
    "OwnerDataLifecycleRepository",
    "OwnerDataLifecycleService",
]
