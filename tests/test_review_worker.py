from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Event
from typing import cast
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.tasks.models import (
    ReviewTask,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.recent_review_executor import RecentReviewTaskExecutionResult
from tests.test_terminal_conversation_turns import turn as terminal_turn
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.workers.polling import PollingPolicy
from app.workers.review_worker import (
    ReviewTaskExecutor,
    ReviewWorker,
    ReviewWorkerError,
    WorkerIterationStatus,
)
from scripts.run_review_worker import main as worker_cli_main


NOW = datetime(2026, 8, 18, 5, 0, 0, tzinfo=timezone.utc)


def running_task(number: int, *, worker_id: str = "worker-1") -> ReviewTask:
    created = NOW + timedelta(seconds=number)
    claimed = created + timedelta(seconds=1)
    return ReviewTask(
        task_id=UUID(f"30000000-0000-4000-8000-{number:012d}"),
        run_id=f"review_worker_{number}",
        task_kind="recent_review",
        schema_version="1.0",
        owner_id="owner-1",
        idempotency_key=f"request-{number}",
        request_fingerprint=f"{number:064x}",
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        status=TaskStatus.RUNNING,
        worker_id=worker_id,
        created_at=created,
        updated_at=claimed,
        claimed_at=claimed,
        finished_at=None,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
        trace_reference=None,
        receipt_reference=None,
        artifact_reference=None,
    )


def successful_terminal(
    *,
    run_id: str = "review_worker_1",
) -> TaskTerminal:
    return TaskTerminal(
        run_id=run_id,
        terminal_reason="quality_gate_passed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        trace_reference=RuntimeTraceReference(
            run_id=run_id,
            sha256="a" * 64,
        ),
        receipt_reference=RunReceiptReference(
            run_id=run_id,
            sha256="b" * 64,
        ),
        artifact_reference=RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="c" * 64,
            producer="review_harness.publisher",
        ),
    )


def test_task_terminal_is_strict_and_rejected_report_is_impossible() -> None:
    with pytest.raises(ValidationError):
        TaskTerminal(
            run_id="review_worker_rejected",
            terminal_reason="quality_gate_passed",
            publication_status=TaskPublicationStatus.REJECTED,
            report_available=True,
            trace_reference=RuntimeTraceReference(
                run_id="review_worker_rejected",
                sha256="a" * 64,
            ),
            receipt_reference=RunReceiptReference(
                run_id="review_worker_rejected",
                sha256="b" * 64,
            ),
            artifact_reference=RuntimeArtifactReference(
                kind="final_report",
                schema_version="1.0",
                relative_path="output/final_report.md",
                sha256="c" * 64,
                producer="review_harness.publisher",
            ),
        )
    with pytest.raises(ValidationError):
        TaskTerminal.model_validate(
            {
                "terminal_reason": "unsafe reason body",
                "publication_status": TaskPublicationStatus.PUBLISHED,
                "report_available": True,
            }
        )


class FakeRepository:
    def __init__(self, claims: list[ReviewTask | None] | None = None) -> None:
        self.claims = list(claims or [])
        self.claim_calls: list[tuple[str, datetime]] = []
        self.succeed_calls: list[tuple[UUID, str, TaskTerminal]] = []
        self.fail_calls: list[tuple[UUID, str, str]] = []
        self.succeed_result = True
        self.fail_result = True
        self.claim_error: Exception | None = None
        self.terminal_error: Exception | None = None

    def claim_next(self, *, worker_id: str, now: datetime) -> ReviewTask | None:
        self.claim_calls.append((worker_id, now))
        if self.claim_error is not None:
            raise self.claim_error
        return self.claims.pop(0) if self.claims else None

    def succeed(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        terminal: TaskTerminal,
    ) -> bool:
        self.succeed_calls.append((task_id, worker_id, terminal))
        if self.terminal_error is not None:
            raise self.terminal_error
        return self.succeed_result

    def fail(self, *, task_id: UUID, worker_id: str, reason: str) -> bool:
        self.fail_calls.append((task_id, worker_id, reason))
        if self.terminal_error is not None:
            raise self.terminal_error
        return self.fail_result


class FakeExecutor:
    def __init__(
        self,
        *,
        terminal: TaskTerminal | None = None,
        error: Exception | None = None,
        on_execute: object | None = None,
    ) -> None:
        self.terminal = terminal or successful_terminal()
        self.error = error
        self.on_execute = on_execute
        self.tasks: list[ReviewTask] = []

    def execute(self, task: ReviewTask) -> TaskTerminal:
        self.tasks.append(task)
        if callable(self.on_execute):
            self.on_execute()
        if self.error is not None:
            raise self.error
        return self.terminal


class StopAfterWaits:
    def __init__(self, count: int) -> None:
        self._remaining = count
        self._stopped = False
        self.waits: list[float] = []

    def is_set(self) -> bool:
        return self._stopped

    def wait(self, timeout: float) -> bool:
        self.waits.append(timeout)
        self._remaining -= 1
        if self._remaining <= 0:
            self._stopped = True
        return self._stopped


def worker(
    repository: FakeRepository,
    executor: FakeExecutor | None = None,
    *,
    policy: PollingPolicy | None = None,
    terminal_turn_writer=None,
) -> ReviewWorker:
    return ReviewWorker(
        repository=cast(object, repository),
        executor=cast(ReviewTaskExecutor, executor or FakeExecutor()),
        worker_id="worker-1",
        clock=lambda: NOW,
        polling_policy=policy or PollingPolicy(jitter_ratio=0.0),
        random_source=lambda: 0.5,
        terminal_turn_writer=terminal_turn_writer,
    )


class FakeTerminalTurnWriter:
    def __init__(self) -> None:
        self.turns = []

    def write(self, value):
        self.turns.append(value)
        return SimpleNamespace(message_id=value.source_task_id)


def test_run_once_is_idle_without_calling_executor_or_terminal_cas() -> None:
    repository = FakeRepository([None])
    executor = FakeExecutor()

    result = worker(repository, executor).run_once()

    assert result.status is WorkerIterationStatus.IDLE
    assert result.task_id is None
    assert executor.tasks == []
    assert repository.succeed_calls == []
    assert repository.fail_calls == []


def test_run_once_executes_claimed_task_and_commits_success_with_owner() -> None:
    task = running_task(1)
    terminal = successful_terminal()
    repository = FakeRepository([task])
    executor = FakeExecutor(terminal=terminal)

    result = worker(repository, executor).run_once()

    assert result.status is WorkerIterationStatus.SUCCEEDED
    assert result.task_id == task.task_id
    assert executor.tasks == [task]
    assert repository.succeed_calls == [(task.task_id, "worker-1", terminal)]
    assert repository.fail_calls == []


def test_run_once_projects_terminal_turn_only_after_successful_task_cas() -> None:
    task = running_task(1)
    base = successful_terminal()
    projected = RecentReviewTaskExecutionResult(
        **base.model_dump(mode="python"),
        terminal_turn=terminal_turn(),
    )
    repository = FakeRepository([task])
    sink = FakeTerminalTurnWriter()

    result = worker(
        repository,
        FakeExecutor(terminal=projected),
        terminal_turn_writer=sink,
    ).run_once()

    assert result.status is WorkerIterationStatus.SUCCEEDED
    assert sink.turns == [projected.terminal_turn]


def test_ownership_loss_never_projects_terminal_turn() -> None:
    task = running_task(1)
    base = successful_terminal()
    projected = RecentReviewTaskExecutionResult(
        **base.model_dump(mode="python"),
        terminal_turn=terminal_turn(),
    )
    repository = FakeRepository([task])
    repository.succeed_result = False
    sink = FakeTerminalTurnWriter()

    result = worker(
        repository,
        FakeExecutor(terminal=projected),
        terminal_turn_writer=sink,
    ).run_once()

    assert result.status is WorkerIterationStatus.OWNERSHIP_LOST
    assert sink.turns == []


def test_executor_exception_marks_task_failed_once_without_leaking_detail() -> None:
    task = running_task(1)
    repository = FakeRepository([task])
    executor = FakeExecutor(error=RuntimeError("provider-secret-response"))

    result = worker(repository, executor).run_once()

    assert result.status is WorkerIterationStatus.FAILED
    assert result.task_id == task.task_id
    assert repository.fail_calls == [
        (task.task_id, "worker-1", "worker_execution_failed")
    ]
    assert repository.succeed_calls == []
    assert "provider-secret-response" not in repr(result)


def test_invalid_executor_terminal_is_failed_without_automatic_retry() -> None:
    task = running_task(1)
    repository = FakeRepository([task, None])
    executor = FakeExecutor()
    executor.terminal = cast(TaskTerminal, object())

    result = worker(repository, executor).run_once()

    assert result.status is WorkerIterationStatus.FAILED
    assert executor.tasks == [task]
    assert repository.fail_calls == [
        (task.task_id, "worker-1", "worker_execution_failed")
    ]
    assert len(repository.claim_calls) == 1


def test_executor_terminal_for_a_different_run_fails_closed() -> None:
    task = running_task(1)
    repository = FakeRepository([task])
    executor = FakeExecutor(
        terminal=successful_terminal(run_id="review_different_run")
    )

    result = worker(repository, executor).run_once()

    assert result.status is WorkerIterationStatus.FAILED
    assert repository.succeed_calls == []
    assert repository.fail_calls == [
        (task.task_id, "worker-1", "worker_execution_failed")
    ]


@pytest.mark.parametrize("terminal_method", ("succeed", "fail"))
def test_stale_or_wrong_owner_terminal_cas_is_reported_without_retry(
    terminal_method: str,
) -> None:
    task = running_task(1)
    repository = FakeRepository([task])
    if terminal_method == "succeed":
        repository.succeed_result = False
        executor = FakeExecutor()
    else:
        repository.fail_result = False
        executor = FakeExecutor(error=RuntimeError("controlled failure"))

    result = worker(repository, executor).run_once()

    assert result.status is WorkerIterationStatus.OWNERSHIP_LOST
    assert result.task_id == task.task_id
    assert len(repository.claim_calls) == 1


@pytest.mark.parametrize("phase", ("claim", "terminal"))
def test_repository_failure_stops_worker_with_only_allowlisted_error(
    phase: str,
) -> None:
    task = running_task(1)
    repository = FakeRepository([task])
    if phase == "claim":
        repository.claim_error = RuntimeError("postgresql://secret@host")
    else:
        repository.terminal_error = RuntimeError("postgresql://secret@host")

    with pytest.raises(ReviewWorkerError) as exc_info:
        worker(repository).run_once()

    expected = (
        "task_claim_failed" if phase == "claim" else "task_terminal_update_failed"
    )
    assert exc_info.value.code == expected
    assert str(exc_info.value) == expected
    assert "postgresql" not in repr(exc_info.value)


def test_run_forever_uses_interruptible_backoff_and_does_not_busy_poll() -> None:
    repository = FakeRepository()
    stop = StopAfterWaits(3)
    policy = PollingPolicy(
        initial_delay_s=0.1,
        maximum_delay_s=1.0,
        multiplier=2.0,
        jitter_ratio=0.0,
    )

    worker(repository, policy=policy).run_forever(stop)

    assert stop.waits == pytest.approx([0.1, 0.2, 0.4])
    assert len(repository.claim_calls) == 3


def test_successful_work_resets_idle_backoff() -> None:
    task = running_task(1)
    repository = FakeRepository([None, task, None, None])
    stop = StopAfterWaits(3)
    policy = PollingPolicy(
        initial_delay_s=0.1,
        maximum_delay_s=1.0,
        multiplier=2.0,
        jitter_ratio=0.0,
    )

    worker(repository, policy=policy).run_forever(stop)

    assert stop.waits == pytest.approx([0.1, 0.1, 0.2])
    assert len(repository.claim_calls) == 4


def test_graceful_shutdown_finishes_current_task_then_claims_no_new_work() -> None:
    stop = Event()
    first = running_task(1)
    second = running_task(2)
    repository = FakeRepository([first, second])
    executor = FakeExecutor(on_execute=stop.set)

    worker(repository, executor).run_forever(stop)

    assert executor.tasks == [first]
    assert repository.succeed_calls[0][0] == first.task_id
    assert len(repository.claim_calls) == 1


def test_already_stopped_worker_never_claims() -> None:
    stop = Event()
    stop.set()
    repository = FakeRepository([running_task(1)])

    worker(repository).run_forever(stop)

    assert repository.claim_calls == []


def test_cli_fails_closed_before_claim_when_environment_is_missing() -> None:
    assert worker_cli_main(["--worker-id", "worker-1"], environment={}) == 2
