"""Owner-scoped application service for persisted product evidence."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol

from app.evidence.ports import (
    EvidenceSnapshotRepository,
    EvidenceSnapshotRepositoryError,
)
from app.evidence.storage import (
    EvidenceSnapshotView,
    ProductRunState,
    project_evidence_snapshot,
    project_product_run_state,
)
from app.tasks.models import ReviewTaskView
from app.tasks.service import TaskServiceError


class TaskRunLookup(Protocol):
    def get_task_by_run_id(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> ReviewTaskView: ...


class EvidenceProductServiceError(RuntimeError):
    """Stable error code boundary; original adapter errors never escape."""

    _CODES = frozenset(
        {
            "run_not_found",
            "evidence_not_available",
            "evidence_integrity_failed",
            "evidence_unavailable",
        }
    )

    def __init__(self, code: str) -> None:
        if code not in self._CODES:
            raise ValueError("unsupported evidence product service error code")
        self.code = code
        super().__init__(code)


class EvidenceProductService:
    def __init__(
        self,
        *,
        task_service: TaskRunLookup,
        repository: EvidenceSnapshotRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not callable(getattr(task_service, "get_task_by_run_id", None)):
            raise TypeError("task_service must expose get_task_by_run_id()")
        if not callable(getattr(repository, "get_latest", None)):
            raise TypeError("repository must expose get_latest()")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._task_service = task_service
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def get_evidence(self, *, owner_id: str, run_id: str) -> EvidenceSnapshotView:
        task = self._get_task(owner_id=owner_id, run_id=run_id)
        snapshot = self._get_snapshot(owner_id=owner_id, run_id=task.run_id)
        if snapshot is None:
            raise EvidenceProductServiceError("evidence_not_available")
        self._require_identity(task, snapshot.task_id, snapshot.run_id)
        try:
            return project_evidence_snapshot(snapshot, now=self._clock())
        except Exception:
            raise EvidenceProductServiceError("evidence_integrity_failed") from None

    def get_product_state(self, *, owner_id: str, run_id: str) -> ProductRunState:
        task = self._get_task(owner_id=owner_id, run_id=run_id)
        snapshot = self._get_snapshot(owner_id=owner_id, run_id=task.run_id)
        if snapshot is not None:
            self._require_identity(task, snapshot.task_id, snapshot.run_id)
        try:
            return project_product_run_state(task, snapshot, now=self._clock())
        except Exception:
            raise EvidenceProductServiceError("evidence_integrity_failed") from None

    def _get_task(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        try:
            task = self._task_service.get_task_by_run_id(
                owner_id=owner_id,
                run_id=run_id,
            )
        except TaskServiceError as error:
            code = "run_not_found" if error.code == "task_not_found" else "evidence_unavailable"
            raise EvidenceProductServiceError(code) from None
        except Exception:
            raise EvidenceProductServiceError("evidence_unavailable") from None
        if not isinstance(task, ReviewTaskView) or task.run_id != run_id:
            raise EvidenceProductServiceError("evidence_integrity_failed")
        return task

    def _get_snapshot(self, *, owner_id: str, run_id: str):
        try:
            return self._repository.get_latest(owner_id=owner_id, run_id=run_id)
        except EvidenceSnapshotRepositoryError as error:
            code = (
                "evidence_integrity_failed"
                if str(error) == "evidence_snapshot_integrity_failed"
                else "evidence_unavailable"
            )
            raise EvidenceProductServiceError(code) from None
        except Exception:
            raise EvidenceProductServiceError("evidence_unavailable") from None

    @staticmethod
    def _require_identity(task: ReviewTaskView, task_id, run_id: str) -> None:
        if task_id != task.task_id or run_id != task.run_id:
            raise EvidenceProductServiceError("evidence_integrity_failed")


__all__ = ["EvidenceProductService", "EvidenceProductServiceError"]
