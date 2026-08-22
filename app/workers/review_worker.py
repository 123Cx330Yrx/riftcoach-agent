from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from threading import Event, Lock, Thread
from typing import Literal, Protocol, TypeAlias
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.tasks.models import ReviewTask, TaskStatus, TaskTerminal, WorkerId
from app.tasks.ports import TaskRepository
from app.tasks.reliable_runtime import (
    TaskCheckpointPhase,
    TaskHeartbeatDisposition,
    TaskHeartbeatResult,
    TaskLeasePolicy,
)
from app.workers.polling import PollingPolicy
from app.tasks.observability import TaskObservability


Clock = Callable[[], datetime]
RandomSource = Callable[[], float]
ReviewWorkerErrorCode: TypeAlias = Literal[
    "task_claim_failed",
    "task_claim_invalid",
    "task_terminal_update_failed",
    "task_lease_update_failed",
    "task_recovery_failed",
    "polling_control_failed",
]
_ERROR_CODES = frozenset(
    {
        "task_claim_failed",
        "task_claim_invalid",
        "task_terminal_update_failed",
        "task_lease_update_failed",
        "task_recovery_failed",
        "polling_control_failed",
    }
)
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)


class ReviewTaskExecutor(Protocol):
    def execute(self, task: ReviewTask) -> TaskTerminal: ...


class TerminalTurnWriter(Protocol):
    def write(self, turn: object) -> object: ...


class ExpiredTaskRecovery(Protocol):
    def recover_batch(self, *, now: datetime) -> tuple[object, ...]: ...


class StopSignal(Protocol):
    def is_set(self) -> bool: ...

    def wait(self, timeout: float) -> bool: ...


class ReviewWorkerError(RuntimeError):
    def __init__(self, code: ReviewWorkerErrorCode) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported review worker error code")
        self.code = code
        super().__init__(code)


class WorkerIterationStatus(StrEnum):
    IDLE = "idle"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OWNERSHIP_LOST = "ownership_lost"


@dataclass(frozen=True, slots=True)
class WorkerIterationResult:
    status: WorkerIterationStatus
    task_id: UUID | None

    def __post_init__(self) -> None:
        if self.status is WorkerIterationStatus.IDLE:
            if self.task_id is not None:
                raise ValueError("idle iteration cannot include task_id")
        elif not isinstance(self.task_id, UUID):
            raise ValueError("non-idle iteration requires task_id")


class _LeaseMaintainer:
    """Keep one synchronous execution fenced without leaking exceptions."""

    def __init__(
        self,
        *,
        repository: TaskRepository,
        task: ReviewTask,
        policy: TaskLeasePolicy,
        clock: Clock,
    ) -> None:
        if task.lease is None:
            raise ValueError("lease maintainer requires a live task lease")
        self._repository = repository
        self._task = task
        self._lease = task.lease
        self._policy = policy
        self._clock = clock
        self._stop = Event()
        self._lock = Lock()
        self._disposition = TaskHeartbeatDisposition.ACTIVE
        self._error: BaseException | None = None
        self._thread = Thread(
            target=self._run,
            name=f"riftcoach-lease-{task.task_id}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def finish(self) -> TaskHeartbeatDisposition:
        self._stop.set()
        self._thread.join(timeout=max(1.0, self._policy.heartbeat_seconds * 2.0))
        if self._thread.is_alive():
            raise RuntimeError("lease heartbeat thread did not stop")
        with self._lock:
            error = self._error
            disposition = self._disposition
        if error is not None:
            raise RuntimeError("lease heartbeat failed") from None
        if disposition is TaskHeartbeatDisposition.LOST:
            return disposition
        return self._beat()

    def _run(self) -> None:
        while not self._stop.wait(self._policy.heartbeat_seconds):
            try:
                disposition = self._beat()
            except BaseException as error:
                with self._lock:
                    self._error = error
                self._stop.set()
                return
            if disposition is TaskHeartbeatDisposition.LOST:
                self._stop.set()
                return

    def _beat(self) -> TaskHeartbeatDisposition:
        result = self._repository.heartbeat(
            task_id=self._task.task_id,
            worker_id=self._lease.worker_id,
            lease_generation=self._lease.generation,
            lease_token=self._lease.private_token,
            now=self._clock(),
            lease_seconds=self._policy.lease_seconds,
        )
        if not isinstance(result, TaskHeartbeatResult) or (
            result.task_id != self._task.task_id
        ):
            raise TypeError("repository returned an invalid heartbeat result")
        with self._lock:
            self._disposition = result.disposition
        return result.disposition


class ReviewWorker:
    def __init__(
        self,
        *,
        repository: TaskRepository,
        executor: ReviewTaskExecutor,
        worker_id: str,
        clock: Clock | None = None,
        polling_policy: PollingPolicy | None = None,
        random_source: RandomSource | None = None,
        observability: TaskObservability | None = None,
        terminal_turn_writer: TerminalTurnWriter | None = None,
        lease_policy: TaskLeasePolicy | None = None,
        recovery: ExpiredTaskRecovery | None = None,
    ) -> None:
        for method_name in (
            "claim_next",
            "heartbeat",
            "save_checkpoint",
            "succeed",
            "fail",
            "cancel_running",
        ):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(getattr(executor, "execute", None)):
            raise TypeError("executor must expose execute()")
        try:
            normalized_worker_id = _WORKER_ID_ADAPTER.validate_python(
                worker_id,
                strict=True,
            )
        except (TypeError, ValueError, ValidationError):
            raise TypeError("worker_id must be a bounded safe identifier") from None
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        if polling_policy is not None and not isinstance(
            polling_policy,
            PollingPolicy,
        ):
            raise TypeError("polling_policy must be a PollingPolicy")
        if random_source is not None and not callable(random_source):
            raise TypeError("random_source must be callable")
        if observability is not None and not isinstance(
            observability,
            TaskObservability,
        ):
            raise TypeError("observability must be a TaskObservability")
        if lease_policy is not None and not isinstance(
            lease_policy,
            TaskLeasePolicy,
        ):
            raise TypeError("lease_policy must be a TaskLeasePolicy")
        if recovery is not None and not callable(
            getattr(recovery, "recover_batch", None)
        ):
            raise TypeError("recovery must expose recover_batch()")

        self._repository = repository
        self._executor = executor
        self._worker_id = normalized_worker_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._polling_policy = polling_policy or PollingPolicy()
        self._random_source = random_source or random.random
        self._observability = observability
        self._lease_policy = lease_policy or TaskLeasePolicy()
        self._recovery = recovery
        if terminal_turn_writer is not None and not callable(
            getattr(terminal_turn_writer, "write", None)
        ):
            raise TypeError("terminal_turn_writer must expose write()")
        self._terminal_turn_writer = terminal_turn_writer

    def run_once(self) -> WorkerIterationResult:
        if self._recovery is not None:
            try:
                recovered = self._recovery.recover_batch(now=self._clock())
            except Exception:
                self._observe("worker.recovery_failed", {})
                raise ReviewWorkerError("task_recovery_failed") from None
            if not isinstance(recovered, tuple):
                self._observe("worker.recovery_failed", {})
                raise ReviewWorkerError("task_recovery_failed")
            self._observe(
                "worker.recovery_batch",
                {"candidate_count": len(recovered)},
            )
        claim_started = time.perf_counter()
        try:
            claimed = self._repository.claim_next(
                worker_id=self._worker_id,
                now=self._clock(),
                lease_seconds=self._lease_policy.lease_seconds,
            )
        except Exception:
            self._observe("worker.claim_failed", {"outcome": "failed"})
            raise ReviewWorkerError("task_claim_failed") from None
        if claimed is None:
            self._observe("worker.idle", {"status": "idle"})
            return WorkerIterationResult(
                status=WorkerIterationStatus.IDLE,
                task_id=None,
            )
        if (
            not isinstance(claimed, ReviewTask)
            or claimed.status is not TaskStatus.RUNNING
            or claimed.worker_id != self._worker_id
            or claimed.lease is None
            or claimed.lease.worker_id != self._worker_id
        ):
            self._observe("worker.claim_invalid", {"outcome": "failed"})
            raise ReviewWorkerError("task_claim_invalid")

        self._observe(
            "worker.claimed",
            {
                "task_id": str(claimed.task_id),
                "run_id": claimed.run_id,
                "worker_id": self._worker_id,
                "queue_delay_ms": max(
                    0.0,
                    (claimed.claimed_at - claimed.created_at).total_seconds() * 1000,
                ),
            },
        )
        if self._observability is not None:
            self._observability.observe_latency(
                "worker.claim",
                max(0.0, (time.perf_counter() - claim_started) * 1000),
            )

        lease = claimed.lease
        try:
            checkpointed = self._repository.save_checkpoint(
                task_id=claimed.task_id,
                worker_id=self._worker_id,
                lease_generation=lease.generation,
                lease_token=lease.private_token,
                checkpoint_id=f"execution-started-{lease.generation}",
                phase=TaskCheckpointPhase.EXECUTION_STARTED,
                now=self._clock(),
            )
        except Exception:
            self._observe(
                "worker.checkpoint_failed",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
            raise ReviewWorkerError("task_lease_update_failed") from None
        if not checkpointed:
            return WorkerIterationResult(
                status=WorkerIterationStatus.OWNERSHIP_LOST,
                task_id=claimed.task_id,
            )

        maintainer = _LeaseMaintainer(
            repository=self._repository,
            task=claimed,
            policy=self._lease_policy,
            clock=self._clock,
        )
        maintainer.start()
        terminal: object | None = None
        execution_failed = False
        try:
            terminal = self._executor.execute(claimed)
        except Exception:
            execution_failed = True
            self._observe(
                "worker.execution_failed",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
        try:
            lease_disposition = maintainer.finish()
        except Exception:
            self._observe(
                "worker.heartbeat_failed",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
            raise ReviewWorkerError("task_lease_update_failed") from None
        if lease_disposition is TaskHeartbeatDisposition.LOST:
            return WorkerIterationResult(
                status=WorkerIterationStatus.OWNERSHIP_LOST,
                task_id=claimed.task_id,
            )
        if lease_disposition is TaskHeartbeatDisposition.CANCEL_REQUESTED:
            return self._commit_cancel(claimed)
        if execution_failed:
            return self._commit_failure(claimed)
        if (
            not isinstance(terminal, TaskTerminal)
            or terminal.run_id != claimed.run_id
        ):
            self._observe(
                "worker.terminal_invalid",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
            return self._commit_failure(claimed)

        try:
            accepted = self._repository.succeed(
                task_id=claimed.task_id,
                worker_id=self._worker_id,
                lease_generation=lease.generation,
                lease_token=lease.private_token,
                now=self._clock(),
                terminal=terminal,
            )
        except Exception:
            self._observe(
                "worker.terminal_update_failed",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
            raise ReviewWorkerError("task_terminal_update_failed") from None
        self._observe(
            "worker.terminal_committed",
            {
                "task_id": str(claimed.task_id),
                "run_id": claimed.run_id,
                "outcome": "succeeded" if accepted else "ownership_lost",
            },
        )
        if not accepted:
            return self._commit_cancel(claimed)
        terminal_turn = getattr(terminal, "terminal_turn", None)
        if (
            accepted
            and terminal_turn is not None
            and self._terminal_turn_writer is not None
        ):
            try:
                projection = self._terminal_turn_writer.write(terminal_turn)
            except Exception:
                self._observe(
                    "worker.terminal_projection_failed",
                    {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
                )
                raise ReviewWorkerError("task_terminal_update_failed") from None
            if getattr(projection, "message_id", None) is None:
                self._observe(
                    "worker.terminal_projection_failed",
                    {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
                )
                raise ReviewWorkerError("task_terminal_update_failed")
        return WorkerIterationResult(
            status=(
                WorkerIterationStatus.SUCCEEDED
                if accepted
                else WorkerIterationStatus.OWNERSHIP_LOST
            ),
            task_id=claimed.task_id,
        )

    def run_forever(self, stop_signal: StopSignal) -> None:
        if not callable(getattr(stop_signal, "is_set", None)) or not callable(
            getattr(stop_signal, "wait", None)
        ):
            raise TypeError("stop_signal must expose is_set() and wait()")

        idle_count = 0
        while self._is_stopped(stop_signal) is False:
            result = self.run_once()
            if result.status is not WorkerIterationStatus.IDLE:
                idle_count = 0
                continue

            idle_count += 1
            try:
                delay = self._polling_policy.delay_for_idle(
                    idle_count=idle_count,
                    jitter_unit=self._random_source(),
                )
                if stop_signal.wait(delay):
                    return
            except Exception:
                raise ReviewWorkerError("polling_control_failed") from None

    def _commit_failure(self, claimed: ReviewTask) -> WorkerIterationResult:
        if claimed.lease is None:
            raise ReviewWorkerError("task_claim_invalid")
        try:
            accepted = self._repository.fail(
                task_id=claimed.task_id,
                worker_id=self._worker_id,
                lease_generation=claimed.lease.generation,
                lease_token=claimed.lease.private_token,
                now=self._clock(),
                reason="worker_execution_failed",
            )
        except Exception:
            self._observe(
                "worker.failure_update_failed",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
            raise ReviewWorkerError("task_terminal_update_failed") from None
        self._observe(
            "worker.failed",
            {
                "task_id": str(claimed.task_id),
                "run_id": claimed.run_id,
                "outcome": "failed" if accepted else "ownership_lost",
            },
        )
        if not accepted:
            return self._commit_cancel(claimed)
        return WorkerIterationResult(
            status=(
                WorkerIterationStatus.FAILED
                if accepted
                else WorkerIterationStatus.OWNERSHIP_LOST
            ),
            task_id=claimed.task_id,
        )

    def _commit_cancel(self, claimed: ReviewTask) -> WorkerIterationResult:
        if claimed.lease is None:
            raise ReviewWorkerError("task_claim_invalid")
        try:
            accepted = self._repository.cancel_running(
                task_id=claimed.task_id,
                worker_id=self._worker_id,
                lease_generation=claimed.lease.generation,
                lease_token=claimed.lease.private_token,
                now=self._clock(),
            )
        except Exception:
            self._observe(
                "worker.cancel_update_failed",
                {"task_id": str(claimed.task_id), "run_id": claimed.run_id},
            )
            raise ReviewWorkerError("task_terminal_update_failed") from None
        self._observe(
            "worker.cancelled",
            {
                "task_id": str(claimed.task_id),
                "run_id": claimed.run_id,
                "outcome": "cancelled" if accepted else "ownership_lost",
            },
        )
        return WorkerIterationResult(
            status=(
                WorkerIterationStatus.CANCELLED
                if accepted
                else WorkerIterationStatus.OWNERSHIP_LOST
            ),
            task_id=claimed.task_id,
        )

    @staticmethod
    def _is_stopped(stop_signal: StopSignal) -> bool:
        try:
            return bool(stop_signal.is_set())
        except Exception:
            raise ReviewWorkerError("polling_control_failed") from None

    def _observe(
        self,
        name: str,
        metadata: dict[str, object],
    ) -> None:
        if self._observability is not None:
            self._observability.emit(name, metadata)


__all__ = [
    "ExpiredTaskRecovery",
    "ReviewTaskExecutor",
    "ReviewWorker",
    "ReviewWorkerError",
    "WorkerIterationResult",
    "WorkerIterationStatus",
]
