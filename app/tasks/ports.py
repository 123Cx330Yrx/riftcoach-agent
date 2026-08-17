from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.tasks.models import (
    PendingReviewTask,
    ReviewTask,
    TaskCapacityPolicy,
    TaskRepositoryCreateResult,
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


__all__ = ["TaskRepository", "TaskRepositoryError"]
