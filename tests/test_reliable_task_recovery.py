from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.tasks.models import (
    ReviewTask,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.reconciliation import (
    ExpiredReviewTaskRecovery,
    ManualRecoveryStatus,
    ManualReviewTaskRecovery,
    TaskRecoveryStatus,
    TaskTerminalEvidenceError,
)
from app.tasks.reliable_runtime import (
    TaskCheckpointPhase,
    TaskCheckpointReference,
    TaskLease,
    TaskLeasePolicy,
)


NOW = datetime(2026, 8, 22, 16, 0, tzinfo=timezone.utc)
TOKEN = "a" * 64


def expired_task(
    *,
    number: int = 1,
    phase: TaskCheckpointPhase = TaskCheckpointPhase.CLAIMED_SAFE,
    cancel_requested: bool = False,
    recovery_count: int = 0,
    status: TaskStatus = TaskStatus.RUNNING,
) -> ReviewTask:
    task_id = UUID(f"83000000-0000-4000-8000-{number:012d}")
    run_id = f"review_recovery_{number}"
    created = NOW - timedelta(minutes=5)
    claimed = NOW - timedelta(minutes=4)
    checkpoint = TaskCheckpointReference(
        checkpoint_id=f"{phase.value}-1",
        run_id=run_id,
        checkpoint_sequence=1,
        lease_generation=1,
        phase=phase,
        safe_to_replay=phase is TaskCheckpointPhase.CLAIMED_SAFE,
        created_at=claimed,
    )
    lease = None
    recovery_required_at = None
    recovery_reason = None
    if status is TaskStatus.RUNNING:
        lease = TaskLease(
            worker_id="worker-recovery-1",
            generation=1,
            token=TOKEN,
            acquired_at=claimed,
            heartbeat_at=claimed,
            expires_at=NOW - timedelta(seconds=1),
        )
    else:
        recovery_required_at = NOW - timedelta(seconds=1)
        recovery_reason = "unsafe_checkpoint"
    return ReviewTask(
        task_id=task_id,
        run_id=run_id,
        task_kind="recent_review",
        schema_version="1.0",
        owner_id="owner-recovery",
        idempotency_key=f"request-{number}",
        request_fingerprint=f"{number:064x}",
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        status=status,
        worker_id="worker-recovery-1",
        created_at=created,
        updated_at=claimed,
        claimed_at=claimed,
        finished_at=None,
        lease_generation=1,
        lease=lease,
        cancel_request_id="cancel-1" if cancel_requested else None,
        cancel_requested_at=claimed if cancel_requested else None,
        cancel_reason="user_requested" if cancel_requested else None,
        checkpoint_sequence=1,
        checkpoint_reference=checkpoint,
        recovery_count=recovery_count,
        recovery_required_at=recovery_required_at,
        recovery_reason=recovery_reason,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
        trace_reference=None,
        receipt_reference=None,
        artifact_reference=None,
    )


def terminal(run_id: str) -> TaskTerminal:
    return TaskTerminal(
        run_id=run_id,
        terminal_reason="quality_gate_passed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        trace_reference=RuntimeTraceReference(run_id=run_id, sha256="b" * 64),
        receipt_reference=RunReceiptReference(run_id=run_id, sha256="c" * 64),
        artifact_reference=RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="d" * 64,
            producer="review_harness.publisher",
        ),
    )


class FakeVerifier:
    def __init__(self, result: TaskTerminal | BaseException):
        self.result = result
        self.calls: list[UUID] = []

    def terminal_for(self, task: ReviewTask) -> TaskTerminal:
        self.calls.append(task.task_id)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class FakeRecoveryRepository:
    def __init__(self, tasks: tuple[ReviewTask, ...], *, accepted: bool = True):
        self.tasks = tasks
        self.accepted = accepted
        self.calls: list[tuple[str, dict[str, object]]] = []

    def list_expired_recovery_candidates(self, *, now, limit):
        self.calls.append(("scan", {"now": now, "limit": limit}))
        return self.tasks

    def cancel_expired(self, **kwargs):
        self.calls.append(("cancel", kwargs))
        return self.accepted

    def reconcile_expired_success(self, **kwargs):
        self.calls.append(("reconcile", kwargs))
        return self.accepted

    def requeue_expired(self, **kwargs):
        self.calls.append(("requeue", kwargs))
        return self.accepted

    def mark_recovery_required(self, **kwargs):
        self.calls.append(("required", kwargs))
        return self.accepted

    def fail_recovery_required(self, **kwargs):
        self.calls.append(("manual", kwargs))
        return self.accepted


def recovery(repository, verifier, *, max_recoveries: int = 3):
    return ExpiredReviewTaskRecovery(
        repository=repository,
        verifier=verifier,
        policy=TaskLeasePolicy(max_recoveries=max_recoveries),
    )


def test_expired_cancel_has_precedence_and_skips_receipt_read() -> None:
    task = expired_task(cancel_requested=True)
    repository = FakeRecoveryRepository((task,))
    verifier = FakeVerifier(AssertionError("receipt must not be read"))

    result = recovery(repository, verifier).recover_batch(now=NOW)

    assert result[0].status is TaskRecoveryStatus.CANCELLED
    assert result[0].reason == "user_requested"
    assert verifier.calls == []
    assert [name for name, _kwargs in repository.calls] == ["scan", "cancel"]


def test_strict_terminal_evidence_reconciles_before_checkpoint_replay() -> None:
    task = expired_task()
    repository = FakeRecoveryRepository((task,))
    verifier = FakeVerifier(terminal(task.run_id))

    result = recovery(repository, verifier).recover_batch(now=NOW)

    assert result[0].status is TaskRecoveryStatus.RECONCILED
    assert result[0].reason == "reconciled"
    assert [name for name, _kwargs in repository.calls] == ["scan", "reconcile"]


def test_missing_receipt_requeues_only_claimed_safe_checkpoint() -> None:
    task = expired_task()
    repository = FakeRecoveryRepository((task,))
    verifier = FakeVerifier(TaskTerminalEvidenceError("receipt_missing"))

    result = recovery(repository, verifier).recover_batch(now=NOW)

    assert result[0].status is TaskRecoveryStatus.REQUEUED
    assert result[0].reason == "claimed_safe"
    assert [name for name, _kwargs in repository.calls] == ["scan", "requeue"]


@pytest.mark.parametrize(
    ("task", "expected_reason"),
    (
        (
            expired_task(phase=TaskCheckpointPhase.EXECUTION_STARTED),
            "unsafe_checkpoint",
        ),
        (expired_task(recovery_count=3), "max_recoveries_exceeded"),
    ),
)
def test_unsafe_or_exhausted_task_requires_manual_recovery(
    task: ReviewTask,
    expected_reason: str,
) -> None:
    repository = FakeRecoveryRepository((task,))
    verifier = FakeVerifier(TaskTerminalEvidenceError("receipt_missing"))

    result = recovery(repository, verifier).recover_batch(now=NOW)

    assert result[0].status is TaskRecoveryStatus.RECOVERY_REQUIRED
    assert result[0].reason == expected_reason
    assert [name for name, _kwargs in repository.calls] == ["scan", "required"]


def test_recovery_cas_loss_is_reported_without_trying_another_mutation() -> None:
    task = expired_task()
    repository = FakeRecoveryRepository((task,), accepted=False)
    verifier = FakeVerifier(terminal(task.run_id))

    result = recovery(repository, verifier).recover_batch(now=NOW)

    assert result[0].status is TaskRecoveryStatus.OWNERSHIP_LOST
    assert result[0].reason == "task_ownership_lost"
    assert [name for name, _kwargs in repository.calls] == ["scan", "reconcile"]


def test_manual_recovery_only_fails_expected_recovery_required_generation() -> None:
    task = expired_task(status=TaskStatus.RECOVERY_REQUIRED)
    repository = FakeRecoveryRepository(())
    recovery_service = ManualReviewTaskRecovery(repository)

    with pytest.raises(ValueError, match="confirmation"):
        recovery_service.recover(
            task_id=task.task_id,
            worker_id=task.worker_id,
            lease_generation=task.lease_generation,
            confirmation_worker_id="other-worker",
        )

    result = recovery_service.recover(
        task_id=task.task_id,
        worker_id=task.worker_id,
        lease_generation=task.lease_generation,
        confirmation_worker_id=task.worker_id,
    )

    assert result.status is ManualRecoveryStatus.RECOVERED
    assert [name for name, _kwargs in repository.calls] == ["manual"]
