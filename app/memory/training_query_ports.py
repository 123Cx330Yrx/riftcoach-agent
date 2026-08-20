from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.memory.training_models import (
    TrainingPlanPage,
    TrainingPlanView,
    TrainingProgressPage,
)


class TrainingQueryRepository(Protocol):
    def list_plans(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> tuple[TrainingPlanView, ...] | None: ...

    def list_progress(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        metric_key: str | None,
        include_history: bool,
        limit: int,
    ) -> TrainingProgressPage | None: ...


class TrainingQueryServicePort(Protocol):
    def plans(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TrainingPlanPage: ...

    def progress(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        metric_key: str | None,
        include_history: bool,
        limit: int,
    ) -> TrainingProgressPage: ...


__all__ = ["TrainingQueryRepository", "TrainingQueryServicePort"]
