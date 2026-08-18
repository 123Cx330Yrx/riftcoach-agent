from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal, Protocol, TypeAlias
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.tasks.models import ReviewTask, TaskStatus, TaskTerminal, WorkerId
from app.tasks.ports import TaskRepository
from app.workers.polling import PollingPolicy


Clock = Callable[[], datetime]
RandomSource = Callable[[], float]
ReviewWorkerErrorCode: TypeAlias = Literal[
    "task_claim_failed",
    "task_claim_invalid",
    "task_terminal_update_failed",
    "polling_control_failed",
]
_ERROR_CODES = frozenset(
    {
        "task_claim_failed",
        "task_claim_invalid",
        "task_terminal_update_failed",
        "polling_control_failed",
    }
)
_WORKER_ID_ADAPTER = TypeAdapter(WorkerId)


class ReviewTaskExecutor(Protocol):
    def execute(self, task: ReviewTask) -> TaskTerminal: ...


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
    ) -> None:
        for method_name in ("claim_next", "succeed", "fail"):
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

        self._repository = repository
        self._executor = executor
        self._worker_id = normalized_worker_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._polling_policy = polling_policy or PollingPolicy()
        self._random_source = random_source or random.random

    def run_once(self) -> WorkerIterationResult:
        try:
            claimed = self._repository.claim_next(
                worker_id=self._worker_id,
                now=self._clock(),
            )
        except Exception:
            raise ReviewWorkerError("task_claim_failed") from None
        if claimed is None:
            return WorkerIterationResult(
                status=WorkerIterationStatus.IDLE,
                task_id=None,
            )
        if (
            not isinstance(claimed, ReviewTask)
            or claimed.status is not TaskStatus.RUNNING
            or claimed.worker_id != self._worker_id
        ):
            raise ReviewWorkerError("task_claim_invalid")

        try:
            terminal = self._executor.execute(claimed)
        except Exception:
            return self._commit_failure(claimed)
        if (
            not isinstance(terminal, TaskTerminal)
            or terminal.run_id != claimed.run_id
        ):
            return self._commit_failure(claimed)

        try:
            accepted = self._repository.succeed(
                task_id=claimed.task_id,
                worker_id=self._worker_id,
                terminal=terminal,
            )
        except Exception:
            raise ReviewWorkerError("task_terminal_update_failed") from None
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
        try:
            accepted = self._repository.fail(
                task_id=claimed.task_id,
                worker_id=self._worker_id,
                reason="worker_execution_failed",
            )
        except Exception:
            raise ReviewWorkerError("task_terminal_update_failed") from None
        return WorkerIterationResult(
            status=(
                WorkerIterationStatus.FAILED
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


__all__ = [
    "ReviewTaskExecutor",
    "ReviewWorker",
    "ReviewWorkerError",
    "WorkerIterationResult",
    "WorkerIterationStatus",
]
