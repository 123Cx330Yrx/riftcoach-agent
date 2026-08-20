from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.memory.training_models import (
    MetricDirection,
    TrainingMetricTrendView,
    TrainingPlanPage,
    TrainingPlanStatus,
    TrainingPlanView,
    TrainingProgressPage,
    TrainingProgressStatus,
    TrainingProgressView,
    TrainingTrend,
    TrainingTrendComparison,
)
from app.memory.training_service import TrainingQueryService, TrainingQueryServiceError


NOW = datetime(2026, 8, 21, 16, 0, tzinfo=timezone.utc)
RELATIONSHIP_ID = UUID("40000000-0000-0000-0000-000000000001")
PLAN_ID = UUID("40000000-0000-0000-0000-000000000002")


def _plan() -> TrainingPlanView:
    return TrainingPlanView(
        plan_id=PLAN_ID,
        relationship_id=RELATIONSHIP_ID,
        version=1,
        status=TrainingPlanStatus.ACTIVE,
        payload={
            "title": "Reduce early deaths",
            "objective": "Review positioning",
            "metrics": [
                {
                    "metric_key": "deaths_before_15",
                    "direction": "decrease",
                    "unit": "count",
                    "stable_tolerance": 0.0,
                }
            ],
        },
        created_at=NOW,
        updated_at=NOW,
    )


def _progress() -> TrainingProgressView:
    return TrainingProgressView(
        progress_id=UUID("40000000-0000-0000-0000-000000000003"),
        plan_id=PLAN_ID,
        relationship_id=RELATIONSHIP_ID,
        metric_key="deaths_before_15",
        metric_value=1.0,
        observed_at=NOW,
        source_run_id="training-run-1",
        source_artifact_sha256="a" * 64,
        status=TrainingProgressStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeRepository:
    def __init__(self) -> None:
        self.calls = []
        self.plan_result = (_plan(),)
        self.progress_result = TrainingProgressPage(
            events=(_progress(),),
            trends=(
                TrainingMetricTrendView(
                    metric_key="deaths_before_15",
                    direction=MetricDirection.DECREASE,
                    comparison=TrainingTrendComparison(
                        trend=TrainingTrend.INSUFFICIENT_DATA,
                        sample_count=1,
                    ),
                ),
            ),
        )
        self.error = None

    def list_plans(self, **kwargs):
        self.calls.append(("plans", kwargs))
        if self.error:
            raise self.error
        return self.plan_result

    def list_progress(self, **kwargs):
        self.calls.append(("progress", kwargs))
        if self.error:
            raise self.error
        return self.progress_result


def test_training_service_forwards_owner_scope_and_bounds():
    repository = FakeRepository()
    service = TrainingQueryService(repository)
    assert service.plans(
        owner_id="training-owner",
        relationship_id=RELATIONSHIP_ID,
        include_history=True,
        limit=25,
    ) == TrainingPlanPage(plans=(_plan(),))
    assert service.progress(
        owner_id="training-owner",
        relationship_id=RELATIONSHIP_ID,
        metric_key="deaths_before_15",
        include_history=False,
        limit=10,
    ) == repository.progress_result
    assert repository.calls[0][1]["owner_id"] == "training-owner"


def test_training_service_maps_missing_scope_and_plan_safely():
    repository = FakeRepository()
    repository.plan_result = None
    with pytest.raises(TrainingQueryServiceError) as missing:
        TrainingQueryService(repository).plans(
            owner_id="training-owner",
            relationship_id=RELATIONSHIP_ID,
            include_history=False,
            limit=50,
        )
    assert missing.value.code == "training_scope_not_found"

    repository.plan_result = ()
    with pytest.raises(TrainingQueryServiceError) as no_plan:
        TrainingQueryService(repository).plans(
            owner_id="training-owner",
            relationship_id=RELATIONSHIP_ID,
            include_history=False,
            limit=50,
        )
    assert no_plan.value.code == "training_plan_not_found"


def test_training_service_hides_repository_failures_and_invalid_shapes():
    repository = FakeRepository()
    repository.error = RuntimeError("database password")
    with pytest.raises(TrainingQueryServiceError) as error:
        TrainingQueryService(repository).progress(
            owner_id="training-owner",
            relationship_id=RELATIONSHIP_ID,
            metric_key=None,
            include_history=False,
            limit=50,
        )
    assert error.value.code == "service_unavailable"
    assert "password" not in str(error.value)

    repository.error = None
    repository.progress_result = [_progress()]
    with pytest.raises(TrainingQueryServiceError):
        TrainingQueryService(repository).progress(
            owner_id="training-owner",
            relationship_id=RELATIONSHIP_ID,
            metric_key=None,
            include_history=False,
            limit=50,
        )
