"""Receipt-backed task reconciliation and restricted manual recovery."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
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
from app.tasks.reliable_runtime import (
    TaskCheckpointPhase,
    TaskLeasePolicy,
    TaskRecoveryResult,
    TaskRecoveryStatus,
)


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
    "recovery_candidate_scan_failed",
    "recovery_update_failed",
]
_RECONCILIATION_ERROR_CODES = frozenset(
    {
        "terminal_evidence_read_failed",
        "task_terminal_update_failed",
        "manual_recovery_update_failed",
        "recovery_candidate_scan_failed",
        "recovery_update_failed",
    }
)
Clock = Callable[[], datetime]


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
    """Project complete immutable evidence for one explicitly expired lease."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        verifier: TerminalEvidenceVerifier,
    ) -> None:
        if not callable(getattr(repository, "reconcile_expired_success", None)):
            raise TypeError("repository must expose reconcile_expired_success()")
        if not callable(getattr(verifier, "terminal_for", None)):
            raise TypeError("verifier must expose terminal_for()")
        self._repository = repository
        self._verifier = verifier

    def reconcile(
        self,
        task: ReviewTask,
        *,
        now: datetime,
    ) -> TaskReconciliationResult:
        if not isinstance(task, ReviewTask):
            raise TypeError("task must be a ReviewTask")
        normalized_now = _as_utc(now)
        if (
            task.status is not TaskStatus.RUNNING
            or task.worker_id is None
            or task.lease is None
            or task.lease.expires_at > normalized_now
        ):
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
            accepted = self._repository.reconcile_expired_success(
                task_id=task.task_id,
                worker_id=task.worker_id,
                lease_generation=task.lease.generation,
                lease_token=task.lease.private_token,
                now=normalized_now,
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


class ExpiredReviewTaskRecovery:
    """Recover a bounded expired-lease batch using durable proof only."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        verifier: TerminalEvidenceVerifier,
        policy: TaskLeasePolicy | None = None,
    ) -> None:
        required_methods = (
            "list_expired_recovery_candidates",
            "cancel_expired",
            "reconcile_expired_success",
            "requeue_expired",
            "mark_recovery_required",
        )
        if any(
            not callable(getattr(repository, method_name, None))
            for method_name in required_methods
        ):
            raise TypeError("repository must expose reliable recovery methods")
        if not callable(getattr(verifier, "terminal_for", None)):
            raise TypeError("verifier must expose terminal_for()")
        if policy is not None and not isinstance(policy, TaskLeasePolicy):
            raise TypeError("policy must be a TaskLeasePolicy")
        self._repository = repository
        self._verifier = verifier
        self._policy = policy or TaskLeasePolicy()

    def recover_batch(self, *, now: datetime) -> tuple[TaskRecoveryResult, ...]:
        normalized_now = _as_utc(now)
        try:
            candidates = self._repository.list_expired_recovery_candidates(
                now=normalized_now,
                limit=self._policy.recovery_batch_size,
            )
        except Exception:
            raise TaskReconciliationError(
                "recovery_candidate_scan_failed"
            ) from None
        if not isinstance(candidates, tuple) or any(
            not isinstance(task, ReviewTask) for task in candidates
        ):
            raise TaskReconciliationError("recovery_candidate_scan_failed")
        return tuple(
            self._recover_one(task=task, now=normalized_now)
            for task in candidates
        )

    def _recover_one(
        self,
        *,
        task: ReviewTask,
        now: datetime,
    ) -> TaskRecoveryResult:
        if (
            task.status is not TaskStatus.RUNNING
            or task.worker_id is None
            or task.lease is None
            or task.lease.expires_at > now
        ):
            return self._result(
                task,
                status=TaskRecoveryStatus.OWNERSHIP_LOST,
                reason="task_ownership_lost",
            )
        lease_arguments = {
            "task_id": task.task_id,
            "worker_id": task.worker_id,
            "lease_generation": task.lease.generation,
            "lease_token": task.lease.private_token,
            "now": now,
        }
        if task.cancel_requested_at is not None:
            accepted = self._mutate(
                self._repository.cancel_expired,
                **lease_arguments,
            )
            return self._accepted_result(
                task,
                accepted=accepted,
                status=TaskRecoveryStatus.CANCELLED,
                reason=task.cancel_reason or "user_requested",
            )

        evidence_failure: str | None = None
        try:
            terminal = self._verifier.terminal_for(task)
        except TaskTerminalEvidenceError as error:
            evidence_failure = error.code
        except Exception:
            evidence_failure = "terminal_evidence_read_failed"
        else:
            if terminal.run_id != task.run_id:
                evidence_failure = "terminal_evidence_invalid"
            else:
                accepted = self._mutate(
                    self._repository.reconcile_expired_success,
                    terminal=terminal,
                    **lease_arguments,
                )
                return self._accepted_result(
                    task,
                    accepted=accepted,
                    status=TaskRecoveryStatus.RECONCILED,
                    reason="reconciled",
                )

        checkpoint = task.checkpoint_reference
        if (
            checkpoint is not None
            and checkpoint.phase is TaskCheckpointPhase.CLAIMED_SAFE
            and checkpoint.safe_to_replay
            and task.recovery_count < self._policy.max_recoveries
        ):
            accepted = self._mutate(
                self._repository.requeue_expired,
                max_recoveries=self._policy.max_recoveries,
                **lease_arguments,
            )
            return self._accepted_result(
                task,
                accepted=accepted,
                status=TaskRecoveryStatus.REQUEUED,
                reason="claimed_safe",
            )

        reason = (
            "max_recoveries_exceeded"
            if task.recovery_count >= self._policy.max_recoveries
            else "unsafe_checkpoint"
            if checkpoint is not None
            else evidence_failure or "terminal_evidence_invalid"
        )
        accepted = self._mutate(
            self._repository.mark_recovery_required,
            reason=reason,
            **lease_arguments,
        )
        return self._accepted_result(
            task,
            accepted=accepted,
            status=TaskRecoveryStatus.RECOVERY_REQUIRED,
            reason=reason,
        )

    @staticmethod
    def _result(
        task: ReviewTask,
        *,
        status: TaskRecoveryStatus,
        reason: str,
    ) -> TaskRecoveryResult:
        return TaskRecoveryResult(
            task_id=task.task_id,
            run_id=task.run_id,
            status=status,
            reason=reason,
        )

    @classmethod
    def _accepted_result(
        cls,
        task: ReviewTask,
        *,
        accepted: bool,
        status: TaskRecoveryStatus,
        reason: str,
    ) -> TaskRecoveryResult:
        if not accepted:
            return cls._result(
                task,
                status=TaskRecoveryStatus.OWNERSHIP_LOST,
                reason="task_ownership_lost",
            )
        return cls._result(task, status=status, reason=reason)

    @staticmethod
    def _mutate(operation, **kwargs: object) -> bool:
        try:
            accepted = operation(**kwargs)
        except Exception:
            raise TaskReconciliationError("recovery_update_failed") from None
        if not isinstance(accepted, bool):
            raise TaskReconciliationError("recovery_update_failed")
        return accepted


class ManualRecoveryStatus(StrEnum):
    RECOVERED = "recovered"
    NOT_RECOVERED = "not_recovered"


class ManualRecoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_id: UUID
    status: ManualRecoveryStatus
    reason: Literal[
        "worker_confirmed_dead",
        "task_not_recovery_required_or_identity_mismatch",
    ]


class ManualReviewTaskRecovery:
    """Fail one recovery-required generation after explicit confirmation."""

    def __init__(
        self,
        repository: TaskRepository,
        *,
        clock: Clock | None = None,
    ) -> None:
        if not callable(getattr(repository, "fail_recovery_required", None)):
            raise TypeError("repository must expose fail_recovery_required()")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def recover(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        confirmation_worker_id: str,
    ) -> ManualRecoveryResult:
        if not isinstance(task_id, UUID):
            raise ValueError("task_id must be a UUID")
        if worker_id != confirmation_worker_id:
            raise ValueError("worker confirmation must match worker_id")
        if (
            isinstance(lease_generation, bool)
            or not isinstance(lease_generation, int)
            or lease_generation < 1
        ):
            raise ValueError("lease_generation must be a positive integer")
        try:
            accepted = self._repository.fail_recovery_required(
                task_id=task_id,
                worker_id=worker_id,
                lease_generation=lease_generation,
                now=_as_utc(self._clock()),
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
                else "task_not_recovery_required_or_identity_mismatch"
            ),
        )


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "ExpiredReviewTaskRecovery",
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
    "TaskRecoveryResult",
    "TaskRecoveryStatus",
    "TerminalEvidenceVerifier",
]
