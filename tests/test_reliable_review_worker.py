from __future__ import annotations

import time
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
from app.tasks.reliable_runtime import (
    TaskCheckpointPhase,
    TaskCheckpointReference,
    TaskHeartbeatDisposition,
    TaskHeartbeatResult,
    TaskLease,
    TaskLeasePolicy,
)
from app.workers.review_worker import (
    ReviewWorker,
    ReviewWorkerError,
    WorkerIterationStatus,
)


NOW = datetime(2026, 8, 22, 15, 0, tzinfo=timezone.utc)
TASK_ID = UUID("83000000-0000-4000-8000-000000000001")
TOKEN = "3" * 64


def running_task() -> ReviewTask:
    lease = TaskLease(
        worker_id="worker-reliable-1",
        generation=1,
        token=TOKEN,
        acquired_at=NOW,
        heartbeat_at=NOW,
        expires_at=NOW + timedelta(seconds=120),
    )
    checkpoint = TaskCheckpointReference(
        checkpoint_id="claimed-1-1",
        run_id="review_reliable_worker_1",
        checkpoint_sequence=1,
        lease_generation=1,
        phase=TaskCheckpointPhase.CLAIMED_SAFE,
        safe_to_replay=True,
        created_at=NOW,
    )
    return ReviewTask(
        task_id=TASK_ID,
        run_id="review_reliable_worker_1",
        task_kind="recent_review",
        schema_version="1.0",
        owner_id="owner-reliable-worker",
        idempotency_key="request-reliable-worker",
        request_fingerprint="1" * 64,
        request_payload={"focus": "overall"},
        status=TaskStatus.RUNNING,
        worker_id=lease.worker_id,
        created_at=NOW,
        updated_at=NOW,
        claimed_at=NOW,
        finished_at=None,
        lease_generation=1,
        lease=lease,
        checkpoint_sequence=1,
        checkpoint_reference=checkpoint,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
        trace_reference=None,
        receipt_reference=None,
        artifact_reference=None,
    )


def terminal() -> TaskTerminal:
    run_id = "review_reliable_worker_1"
    return TaskTerminal(
        run_id=run_id,
        terminal_reason="quality_gate_passed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        trace_reference=RuntimeTraceReference(run_id=run_id, sha256="a" * 64),
        receipt_reference=RunReceiptReference(run_id=run_id, sha256="b" * 64),
        artifact_reference=RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="c" * 64,
            producer="review_harness.publisher",
        ),
    )


class Repository:
    def __init__(
        self,
        dispositions=None,
        *,
        succeed_result: bool = True,
        fail_result: bool = True,
        cancel_result: bool = True,
    ) -> None:
        self.claim = running_task()
        self.dispositions = list(
            dispositions or [TaskHeartbeatDisposition.ACTIVE]
        )
        self.claim_calls = []
        self.checkpoints = []
        self.heartbeats = []
        self.succeed_calls = []
        self.fail_calls = []
        self.cancel_calls = []
        self.succeed_result = succeed_result
        self.fail_result = fail_result
        self.cancel_result = cancel_result

    def claim_next(self, **kwargs):
        self.claim_calls.append(kwargs)
        claimed, self.claim = self.claim, None
        return claimed

    def save_checkpoint(self, **kwargs):
        self.checkpoints.append(kwargs)
        return True

    def heartbeat(self, **kwargs):
        self.heartbeats.append(kwargs)
        disposition = (
            self.dispositions.pop(0)
            if len(self.dispositions) > 1
            else self.dispositions[0]
        )
        return TaskHeartbeatResult(
            task_id=TASK_ID,
            disposition=disposition,
            lease_expires_at=(
                None
                if disposition is TaskHeartbeatDisposition.LOST
                else NOW + timedelta(seconds=120)
            ),
        )

    def succeed(self, **kwargs):
        self.succeed_calls.append(kwargs)
        return self.succeed_result

    def fail(self, **kwargs):
        self.fail_calls.append(kwargs)
        return self.fail_result

    def cancel_running(self, **kwargs):
        self.cancel_calls.append(kwargs)
        return self.cancel_result


class Executor:
    def __init__(self, *, delay: float = 0, error: Exception | None = None) -> None:
        self.delay = delay
        self.error = error
        self.tasks = []

    def execute(self, task):
        self.tasks.append(task)
        if self.delay:
            time.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return terminal()


def worker(
    repository: Repository,
    executor: Executor,
    *,
    policy=None,
    recovery=None,
) -> ReviewWorker:
    return ReviewWorker(
        repository=repository,
        executor=executor,
        worker_id="worker-reliable-1",
        clock=lambda: NOW + timedelta(seconds=1),
        lease_policy=policy or TaskLeasePolicy(),
        recovery=recovery,
    )


class Recovery:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls = []

    def recover_batch(self, *, now):
        self.calls.append(now)
        if self.error is not None:
            raise self.error
        return ()


def test_worker_checkpoints_then_heartbeats_and_fences_success() -> None:
    repository = Repository()
    result = worker(repository, Executor()).run_once()

    assert result.status is WorkerIterationStatus.SUCCEEDED
    assert repository.claim_calls[0]["lease_seconds"] == 120
    assert repository.checkpoints[0]["phase"] is TaskCheckpointPhase.EXECUTION_STARTED
    assert len(repository.heartbeats) == 1
    committed = repository.succeed_calls[0]
    assert committed["lease_generation"] == 1
    assert committed["lease_token"] == TOKEN
    assert repository.fail_calls == []
    assert repository.cancel_calls == []


def test_cancel_observed_at_final_heartbeat_takes_precedence_over_success() -> None:
    repository = Repository([TaskHeartbeatDisposition.CANCEL_REQUESTED])
    result = worker(repository, Executor()).run_once()

    assert result.status is WorkerIterationStatus.CANCELLED
    assert repository.succeed_calls == []
    assert repository.fail_calls == []
    assert len(repository.cancel_calls) == 1


def test_lost_lease_rejects_terminal_without_failure_rewrite() -> None:
    repository = Repository([TaskHeartbeatDisposition.LOST])
    result = worker(repository, Executor()).run_once()

    assert result.status is WorkerIterationStatus.OWNERSHIP_LOST
    assert repository.succeed_calls == []
    assert repository.fail_calls == []
    assert repository.cancel_calls == []


def test_executor_failure_uses_the_same_fencing_identity() -> None:
    repository = Repository()
    result = worker(
        repository,
        Executor(error=RuntimeError("provider-private-body")),
    ).run_once()

    assert result.status is WorkerIterationStatus.FAILED
    failed = repository.fail_calls[0]
    assert failed["lease_generation"] == 1
    assert failed["lease_token"] == TOKEN
    assert failed["reason"] == "worker_execution_failed"


def test_long_executor_receives_background_heartbeat_before_final_check() -> None:
    repository = Repository()
    policy = TaskLeasePolicy(lease_seconds=15, heartbeat_seconds=1)

    result = worker(
        repository,
        Executor(delay=1.1),
        policy=policy,
    ).run_once()

    assert result.status is WorkerIterationStatus.SUCCEEDED
    assert len(repository.heartbeats) >= 2


def test_worker_runs_bounded_recovery_before_claiming_new_work() -> None:
    repository = Repository()
    recovery = Recovery()

    result = worker(repository, Executor(), recovery=recovery).run_once()

    assert result.status is WorkerIterationStatus.SUCCEEDED
    assert recovery.calls == [NOW + timedelta(seconds=1)]
    assert len(repository.claim_calls) == 1


def test_recovery_failure_is_body_free_and_blocks_claim() -> None:
    repository = Repository()
    recovery = Recovery(error=RuntimeError("private-receipt-path"))

    with pytest.raises(ReviewWorkerError) as caught:
        worker(repository, Executor(), recovery=recovery).run_once()

    assert caught.value.code == "task_recovery_failed"
    assert repository.claim_calls == []


def test_cancel_arriving_after_final_heartbeat_still_wins_success_cas() -> None:
    repository = Repository(succeed_result=False, cancel_result=True)

    result = worker(repository, Executor()).run_once()

    assert result.status is WorkerIterationStatus.CANCELLED
    assert len(repository.succeed_calls) == 1
    assert len(repository.cancel_calls) == 1


def test_cancel_arriving_during_failure_cas_still_converges_cancelled() -> None:
    repository = Repository(fail_result=False, cancel_result=True)

    result = worker(
        repository,
        Executor(error=RuntimeError("provider-private-body")),
    ).run_once()

    assert result.status is WorkerIterationStatus.CANCELLED
    assert len(repository.fail_calls) == 1
    assert len(repository.cancel_calls) == 1
