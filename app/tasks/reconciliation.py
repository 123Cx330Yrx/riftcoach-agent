"""Receipt-backed task reconciliation and restricted manual recovery."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.harness.models import ArtifactKind
from app.product.run_query import RunQueryError, RunQueryService
from app.product.run_receipts import (
    FileRunReceiptStore,
    RunReceiptReference,
)
from app.runtime.models import RuntimeStatus, RuntimeTraceReference
from app.runtime.store import RuntimeTraceStore
from app.tasks.models import (
    ReviewTask,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.ports import TaskRepository


ReconciliationReason = Literal[
    "reconciled",
    "receipt_missing",
    "terminal_evidence_invalid",
    "terminal_receipt_not_completed",
    "task_ownership_lost",
]
_RECONCILIATION_REASONS = frozenset(
    {
        "reconciled",
        "receipt_missing",
        "terminal_evidence_invalid",
        "terminal_receipt_not_completed",
        "task_ownership_lost",
    }
)
_TERMINAL_EVIDENCE_ERROR_CODES = _RECONCILIATION_REASONS - {
    "reconciled",
    "task_ownership_lost",
}
TaskReconciliationErrorCode: TypeAlias = Literal[
    "terminal_evidence_read_failed",
    "task_terminal_update_failed",
    "manual_recovery_update_failed",
]
_RECONCILIATION_ERROR_CODES = frozenset(
    {
        "terminal_evidence_read_failed",
        "task_terminal_update_failed",
        "manual_recovery_update_failed",
    }
)


class TaskReconciliationError(RuntimeError):
    def __init__(self, code: TaskReconciliationErrorCode) -> None:
        if code not in _RECONCILIATION_ERROR_CODES:
            raise ValueError("unsupported task reconciliation error")
        self.code = code
        super().__init__(code)


class TaskTerminalEvidenceError(RuntimeError):
    """A body-free, allowlisted failure while reading run evidence."""

    def __init__(self, code: ReconciliationReason) -> None:
        if code not in _TERMINAL_EVIDENCE_ERROR_CODES:
            raise ValueError("unsupported terminal evidence error")
        self.code = code
        super().__init__(code)


class ReconciliationStatus(StrEnum):
    RECONCILED = "reconciled"
    RECOVERY_REQUIRED = "recovery_required"
    OWNERSHIP_LOST = "ownership_lost"


class TaskReconciliationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_id: UUID
    run_id: str
    status: ReconciliationStatus
    reason: ReconciliationReason


class TerminalEvidenceVerifier(Protocol):
    def terminal_for(self, task: ReviewTask) -> TaskTerminal: ...


class RecentReviewTerminalEvidenceVerifier:
    """Rebuild a succeeded TaskTerminal from fully verified file evidence."""

    def __init__(
        self,
        runs_root: str | Path,
        *,
        receipt_store: FileRunReceiptStore | None = None,
        query_service: RunQueryService | None = None,
    ) -> None:
        self._runs_root = Path(runs_root).resolve()
        self._receipts = receipt_store or FileRunReceiptStore(self._runs_root)
        self._query = query_service or RunQueryService(
            self._runs_root,
            receipt_store=self._receipts,
        )

    def terminal_for(self, task: ReviewTask) -> TaskTerminal:
        if not isinstance(task, ReviewTask):
            raise TypeError("task must be a ReviewTask")
        if task.status is not TaskStatus.RUNNING or task.worker_id is None:
            raise TaskTerminalEvidenceError("terminal_evidence_invalid")

        try:
            receipt, receipt_reference = self._receipts.read_receipt_with_reference(
                task.run_id
            )
        except FileNotFoundError:
            raise TaskTerminalEvidenceError("receipt_missing") from None
        except Exception:
            raise TaskTerminalEvidenceError("terminal_evidence_invalid") from None

        if (
            receipt.run_id != task.run_id
            or receipt.runtime_status is not RuntimeStatus.COMPLETED
            or receipt.publication_status is None
            or receipt.trace_reference is None
        ):
            raise TaskTerminalEvidenceError(
                "terminal_receipt_not_completed"
            )

        try:
            view = self._query.get_run(task.run_id)
            trace = RuntimeTraceStore(
                self._runs_root,
                task.run_id,
            ).read_trace(receipt.trace_reference)
            confirmed_receipt, confirmed_reference = (
                self._receipts.read_receipt_with_reference(task.run_id)
            )
        except RunQueryError:
            raise TaskTerminalEvidenceError("terminal_evidence_invalid") from None
        except Exception:
            raise TaskTerminalEvidenceError("terminal_evidence_invalid") from None

        if (
            view.run_id != task.run_id
            or view.runtime_status is not RuntimeStatus.COMPLETED
            or view.publication_status is not receipt.publication_status
            or view.terminal_reason != receipt.terminal_reason
            or view.report_available is not receipt.report_available
            or trace.run_id != task.run_id
            or trace.runtime_status is not RuntimeStatus.COMPLETED
            or confirmed_receipt != receipt
            or confirmed_reference != receipt_reference
        ):
            raise TaskTerminalEvidenceError("terminal_evidence_invalid")

        final_references = tuple(
            artifact
            for artifact in trace.artifacts
            if artifact.kind == ArtifactKind.FINAL_REPORT.value
        )
        if receipt.report_available and len(final_references) != 1:
            raise TaskTerminalEvidenceError("terminal_evidence_invalid")
        if not receipt.report_available and final_references:
            raise TaskTerminalEvidenceError("terminal_evidence_invalid")

        publication = TaskPublicationStatus(receipt.publication_status.value)
        return TaskTerminal(
            run_id=task.run_id,
            terminal_reason=receipt.terminal_reason,
            publication_status=publication,
            report_available=receipt.report_available,
            trace_reference=RuntimeTraceReference.model_validate(
                receipt.trace_reference.model_dump(mode="python")
            ),
            receipt_reference=RunReceiptReference.model_validate(
                receipt_reference.model_dump(mode="python")
            ),
            artifact_reference=(
                final_references[0] if final_references else None
            ),
        )


class ReviewTaskReconciler:
    """Never rerun work; only project complete immutable evidence."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        verifier: TerminalEvidenceVerifier,
    ) -> None:
        if not callable(getattr(repository, "succeed", None)):
            raise TypeError("repository must expose succeed()")
        if not callable(getattr(verifier, "terminal_for", None)):
            raise TypeError("verifier must expose terminal_for()")
        self._repository = repository
        self._verifier = verifier

    def reconcile(self, task: ReviewTask) -> TaskReconciliationResult:
        if not isinstance(task, ReviewTask):
            raise TypeError("task must be a ReviewTask")
        if task.status is not TaskStatus.RUNNING or task.worker_id is None:
            return TaskReconciliationResult(
                task_id=task.task_id,
                run_id=task.run_id,
                status=ReconciliationStatus.RECOVERY_REQUIRED,
                reason="terminal_evidence_invalid",
            )

        try:
            terminal = self._verifier.terminal_for(task)
        except TaskTerminalEvidenceError as error:
            return TaskReconciliationResult(
                task_id=task.task_id,
                run_id=task.run_id,
                status=ReconciliationStatus.RECOVERY_REQUIRED,
                reason=error.code,
            )
        except Exception:
            raise TaskReconciliationError(
                "terminal_evidence_read_failed"
            ) from None
        if terminal.run_id != task.run_id:
            return TaskReconciliationResult(
                task_id=task.task_id,
                run_id=task.run_id,
                status=ReconciliationStatus.RECOVERY_REQUIRED,
                reason="terminal_evidence_invalid",
            )

        try:
            accepted = self._repository.succeed(
                task_id=task.task_id,
                worker_id=task.worker_id,
                terminal=terminal,
            )
        except Exception:
            raise TaskReconciliationError(
                "task_terminal_update_failed"
            ) from None
        if not accepted:
            return TaskReconciliationResult(
                task_id=task.task_id,
                run_id=task.run_id,
                status=ReconciliationStatus.OWNERSHIP_LOST,
                reason="task_ownership_lost",
            )
        return TaskReconciliationResult(
            task_id=task.task_id,
            run_id=task.run_id,
            status=ReconciliationStatus.RECONCILED,
            reason="reconciled",
        )


class ManualRecoveryStatus(StrEnum):
    RECOVERED = "recovered"
    NOT_RECOVERED = "not_recovered"


class ManualRecoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_id: UUID
    status: ManualRecoveryStatus
    reason: Literal[
        "worker_confirmed_dead",
        "task_not_running_or_worker_mismatch",
    ]


class ManualReviewTaskRecovery:
    """One explicit, worker-matching CAS; it never requeues or reruns."""

    def __init__(self, repository: TaskRepository) -> None:
        if not callable(getattr(repository, "fail", None)):
            raise TypeError("repository must expose fail()")
        self._repository = repository

    def recover(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        confirmation_worker_id: str,
    ) -> ManualRecoveryResult:
        if not isinstance(task_id, UUID):
            raise ValueError("task_id must be a UUID")
        if worker_id != confirmation_worker_id:
            raise ValueError("worker confirmation must match worker_id")
        try:
            accepted = self._repository.fail(
                task_id=task_id,
                worker_id=worker_id,
                reason="worker_confirmed_dead",
            )
        except Exception:
            raise TaskReconciliationError(
                "manual_recovery_update_failed"
            ) from None
        return ManualRecoveryResult(
            task_id=task_id,
            status=(
                ManualRecoveryStatus.RECOVERED
                if accepted
                else ManualRecoveryStatus.NOT_RECOVERED
            ),
            reason=(
                "worker_confirmed_dead"
                if accepted
                else "task_not_running_or_worker_mismatch"
            ),
        )


__all__ = [
    "ManualRecoveryResult",
    "ManualRecoveryStatus",
    "ManualReviewTaskRecovery",
    "RecentReviewTerminalEvidenceVerifier",
    "ReconciliationStatus",
    "ReviewTaskReconciler",
    "TaskReconciliationResult",
    "TaskReconciliationError",
    "TaskReconciliationErrorCode",
    "TaskTerminalEvidenceError",
    "TerminalEvidenceVerifier",
]
