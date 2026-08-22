from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.tasks.models import (
    PendingConversationReviewTask,
    PendingReviewTask,
    ReviewTask,
    TaskCapacityPolicy,
    TaskRepositoryCreateResult,
    TaskRepositoryDeleteResult,
    TaskTerminal,
)
from app.tasks.reliable_runtime import (
    TaskCancelResult,
    TaskCheckpointPhase,
    TaskEventPage,
    TaskHeartbeatResult,
)


class TaskRepositoryError(RuntimeError):
    """A repository failure that must be remapped before a public boundary."""


class TaskRepository(Protocol):
    def create_or_replay(
        self,
        pending: PendingReviewTask,
        *,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult: ...

    def create_conversation_bound_or_replay(
        self,
        pending: PendingConversationReviewTask,
        *,
        capacity: TaskCapacityPolicy,
    ) -> TaskRepositoryCreateResult: ...

    def get_by_task_id(
        self,
        *,
        owner_id: str,
        task_id: UUID,
    ) -> ReviewTask | None: ...

    def get_by_run_id(
        self,
        *,
        owner_id: str,
        run_id: str,
    ) -> ReviewTask | None: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_seconds: int = 120,
    ) -> ReviewTask | None: ...

    def heartbeat(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        lease_seconds: int,
    ) -> TaskHeartbeatResult: ...

    def save_checkpoint(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        checkpoint_id: str,
        phase: TaskCheckpointPhase,
        now: datetime,
    ) -> bool: ...

    def request_cancel(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        request_id: str,
        reason: str,
        now: datetime,
    ) -> TaskCancelResult | None: ...

    def cancel_running(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
    ) -> bool: ...

    def read_events(
        self,
        *,
        owner_id: str,
        task_id: UUID,
        after_cursor: int = 0,
        limit: int = 50,
    ) -> TaskEventPage | None: ...

    def list_expired_recovery_candidates(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[ReviewTask, ...]: ...

    def cancel_expired(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
    ) -> bool: ...

    def reconcile_expired_success(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        terminal: TaskTerminal,
    ) -> bool: ...

    def requeue_expired(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        max_recoveries: int,
    ) -> bool: ...

    def mark_recovery_required(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        reason: str,
    ) -> bool: ...

    def fail_recovery_required(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        now: datetime,
        reason: str,
    ) -> bool: ...

    def succeed(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        terminal: TaskTerminal,
    ) -> bool: ...

    def fail(
        self,
        *,
        task_id: UUID,
        worker_id: str,
        lease_generation: int,
        lease_token: str,
        now: datetime,
        reason: str,
    ) -> bool: ...

    def delete_terminal(
        self,
        *,
        owner_id: str,
        task_id: UUID,
    ) -> TaskRepositoryDeleteResult: ...


__all__ = ["TaskRepository", "TaskRepositoryError"]
