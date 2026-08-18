"""Owner-scoped task deletion with hidden-before-cleanup semantics."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.harness.run_ids import normalize_run_id
from app.tasks.models import (
    OwnerId,
    TaskDeleteDisposition,
    TaskDeletionResult,
    TaskRepositoryDeleteDisposition,
    TaskRepositoryDeleteResult,
)
from app.tasks.ports import TaskRepositoryError


Clock = Callable[[], datetime]


class TaskDeletionError(RuntimeError):
    """Body-free deletion failure suitable for an API boundary."""

    def __init__(self, code: str) -> None:
        if code not in {
            "task_not_found",
            "task_delete_conflict",
            "task_persistence_failed",
        }:
            raise ValueError("unsupported task deletion error code")
        self.code = code
        super().__init__(code)


class TerminalTaskDeletePort(Protocol):
    def delete_terminal(
        self,
        *,
        owner_id: str,
        task_id: UUID,
    ) -> TaskRepositoryDeleteResult: ...


class RunDataCleaner(Protocol):
    def cleanup(self, run_id: str) -> bool: ...


class FileRunDataCleaner:
    """Delete one run directory and retain only a safe retry marker on error."""

    marker_directory_name = ".deletion_compensation"

    def __init__(
        self,
        runs_root: str | Path,
        *,
        compensation_root: str | Path | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.runs_root = Path(runs_root).expanduser().resolve()
        self.compensation_root = (
            Path(compensation_root).expanduser().resolve()
            if compensation_root is not None
            else self.runs_root / self.marker_directory_name
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        if not callable(self._clock):
            raise TypeError("clock must be callable")

    def cleanup(self, run_id: str) -> bool:
        normalized = normalize_run_id(run_id)
        target = self._run_directory(normalized)
        try:
            if target.is_symlink():
                target.unlink()
            elif target.exists():
                if not target.is_dir():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            self._remove_marker(normalized)
            return True
        except Exception:
            # Do not persist exception text, paths outside the run identity, or
            # any file content.  The SQL row is already hidden by this point.
            self._write_marker(normalized)
            return False

    def retry_pending(self) -> int:
        if not self.compensation_root.is_dir():
            return 0
        completed = 0
        for marker in sorted(self.compensation_root.glob("*.json")):
            try:
                payload = json.loads(marker.read_text(encoding="utf-8"))
                run_id = normalize_run_id(payload.get("run_id"))
            except Exception:
                continue
            if self.cleanup(run_id):
                completed += 1
        return completed

    def has_pending(self, run_id: str) -> bool:
        normalized = normalize_run_id(run_id)
        return self._marker_path(normalized).is_file()

    def _run_directory(self, run_id: str) -> Path:
        target = (self.runs_root / run_id).resolve()
        if not target.is_relative_to(self.runs_root) or target == self.runs_root:
            raise ValueError("run directory must stay below runs_root")
        return target

    def _marker_path(self, run_id: str) -> Path:
        return self.compensation_root / f"{run_id}.json"

    def _write_marker(self, run_id: str) -> None:
        self.compensation_root.mkdir(parents=True, exist_ok=True)
        target = self._marker_path(run_id)
        payload = {
            "schema_version": "1.0",
            "run_id": run_id,
            "recorded_at_utc": _as_utc(self._clock()).isoformat(),
            "retryable": True,
        }
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.compensation_root,
                prefix=".deletion.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _remove_marker(self, run_id: str) -> None:
        marker = self._marker_path(run_id)
        try:
            marker.unlink()
        except FileNotFoundError:
            pass


class TaskDeletionService:
    """Coordinate SQL hiding and post-commit run-data cleanup."""

    def __init__(
        self,
        *,
        repository: TerminalTaskDeletePort,
        cleaner: RunDataCleaner,
        clock: Clock | None = None,
    ) -> None:
        if not callable(getattr(repository, "delete_terminal", None)):
            raise TypeError("repository must expose delete_terminal()")
        if not callable(getattr(cleaner, "cleanup", None)):
            raise TypeError("cleaner must expose cleanup()")
        self._repository = repository
        self._cleaner = cleaner
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def delete(self, *, owner_id: str, task_id: UUID) -> TaskDeletionResult:
        _validate_owner(owner_id)
        if not isinstance(task_id, UUID):
            raise TaskDeletionError("task_not_found")
        try:
            result = self._repository.delete_terminal(
                owner_id=owner_id,
                task_id=task_id,
            )
        except TaskRepositoryError:
            raise TaskDeletionError("task_persistence_failed") from None
        except Exception:
            raise TaskDeletionError("task_persistence_failed") from None

        if not isinstance(result, TaskRepositoryDeleteResult):
            raise TaskDeletionError("task_persistence_failed")
        if result.disposition is TaskRepositoryDeleteDisposition.NOT_FOUND:
            # A second DELETE is deliberately indistinguishable from a missing
            # resource and never reopens any file data.
            return TaskDeletionResult(
                disposition=TaskDeleteDisposition.ALREADY_HIDDEN,
                task_id=task_id,
            )
        if result.run_id is None:
            raise TaskDeletionError("task_persistence_failed")
        if result.disposition is TaskRepositoryDeleteDisposition.ACTIVE_CONFLICT:
            return TaskDeletionResult(
                disposition=TaskDeleteDisposition.ACTIVE_CONFLICT,
                task_id=task_id,
                run_id=result.run_id,
            )

        cleaned = self._cleaner.cleanup(result.run_id)
        return TaskDeletionResult(
            disposition=(
                TaskDeleteDisposition.DELETED
                if cleaned
                else TaskDeleteDisposition.CLEANUP_PENDING
            ),
            task_id=task_id,
            run_id=result.run_id,
        )


def _validate_owner(owner_id: str) -> None:
    from pydantic import TypeAdapter, ValidationError

    try:
        TypeAdapter(OwnerId).validate_python(owner_id, strict=True)
    except (TypeError, ValueError, ValidationError):
        raise TaskDeletionError("task_not_found") from None


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "FileRunDataCleaner",
    "RunDataCleaner",
    "TaskDeleteDisposition",
    "TaskDeletionError",
    "TaskDeletionService",
    "TerminalTaskDeletePort",
]
