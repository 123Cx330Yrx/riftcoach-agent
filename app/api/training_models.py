from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict

from app.memory.training_models import (
    TrainingPlanPage,
    TrainingPlanView,
    TrainingProgressPage,
    TrainingProgressView,
    TrainingMetricTrendView,
)


TrainingApiErrorCode: TypeAlias = Literal[
    "training_scope_not_found",
    "training_plan_not_found",
    "service_unavailable",
]


class TrainingApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TrainingPlanPageResponse(TrainingApiModel):
    schema_version: Literal["1.0"] = "1.0"
    plans: tuple[TrainingPlanView, ...]

    @classmethod
    def from_page(cls, page: TrainingPlanPage):
        if not isinstance(page, TrainingPlanPage):
            raise TypeError("page must be TrainingPlanPage")
        return cls(plans=page.plans)


class TrainingProgressPageResponse(TrainingApiModel):
    schema_version: Literal["1.0"] = "1.0"
    events: tuple[TrainingProgressView, ...]
    trends: tuple[TrainingMetricTrendView, ...]

    @classmethod
    def from_page(cls, page: TrainingProgressPage):
        if not isinstance(page, TrainingProgressPage):
            raise TypeError("page must be TrainingProgressPage")
        return cls(events=page.events, trends=page.trends)


class TrainingErrorResponse(TrainingApiModel):
    code: TrainingApiErrorCode


__all__ = [
    "TrainingApiErrorCode",
    "TrainingErrorResponse",
    "TrainingPlanPageResponse",
    "TrainingProgressPageResponse",
]
