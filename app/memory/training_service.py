from __future__ import annotations

from uuid import UUID

from app.memory.training_models import (
    TrainingPlanPage,
    TrainingPlanView,
    TrainingProgressPage,
)
from app.memory.training_query_ports import TrainingQueryRepository


class TrainingQueryServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        if code not in {
            "training_scope_not_found",
            "training_plan_not_found",
            "service_unavailable",
        }:
            raise ValueError("training query error code is not allowlisted")
        self.code = code
        super().__init__(code)


class TrainingQueryService:
    def __init__(self, repository: TrainingQueryRepository) -> None:
        for method in ("list_plans", "list_progress"):
            if not callable(getattr(repository, method, None)):
                raise TypeError(f"repository must expose {method}()")
        self._repository = repository

    def plans(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TrainingPlanPage:
        try:
            result = self._repository.list_plans(
                owner_id=owner_id,
                relationship_id=relationship_id,
                include_history=include_history,
                limit=limit,
            )
        except Exception:
            raise TrainingQueryServiceError("service_unavailable") from None
        if result is None:
            raise TrainingQueryServiceError("training_scope_not_found")
        if not isinstance(result, tuple) or any(
            not isinstance(item, TrainingPlanView) for item in result
        ):
            raise TrainingQueryServiceError("service_unavailable")
        if not result:
            raise TrainingQueryServiceError("training_plan_not_found")
        return TrainingPlanPage(plans=result)

    def progress(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        metric_key: str | None,
        include_history: bool,
        limit: int,
    ) -> TrainingProgressPage:
        try:
            result = self._repository.list_progress(
                owner_id=owner_id,
                relationship_id=relationship_id,
                metric_key=metric_key,
                include_history=include_history,
                limit=limit,
            )
        except Exception:
            raise TrainingQueryServiceError("service_unavailable") from None
        if result is None:
            raise TrainingQueryServiceError("training_scope_not_found")
        if not isinstance(result, TrainingProgressPage):
            raise TrainingQueryServiceError("service_unavailable")
        return result


__all__ = ["TrainingQueryService", "TrainingQueryServiceError"]
