from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.memory.models import CandidateKind, MemoryOperation, RelationshipRole, TargetScope
from app.memory.training_models import (
    MetricDirection,
    MetricSpecification,
    MetricUnit,
    TrainingContractError,
    TrainingPlanAction,
    TrainingTrend,
    compare_training_trend,
    parse_training_plan_write,
    parse_training_progress_write,
)


PLAN_ID = UUID("10000000-0000-0000-0000-000000000001")
PROGRESS_ID = UUID("20000000-0000-0000-0000-000000000001")


def _plan_payload(**overrides):
    value = {
        "action": "activate",
        "title": "Reduce early deaths",
        "objective": "Review positioning before minute 15",
        "metrics": [
            {
                "metric_key": "deaths_before_15",
                "direction": "decrease",
                "unit": "count",
                "baseline": 2.0,
                "target": 1.0,
                "stable_tolerance": 0.0,
            }
        ],
    }
    value.update(overrides)
    return {"value": value, "expected_version": None}


def _parse_plan(payload=None, *, role=RelationshipRole.SELF):
    return parse_training_plan_write(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.TRAINING_PLAN,
        operation=MemoryOperation.SET,
        relationship_role=role,
        proposal_payload=payload or _plan_payload(),
    )


def _progress_payload(**overrides):
    value = {
        "plan_id": str(PLAN_ID),
        "metric_key": "deaths_before_15",
        "metric_value": 1.0,
        "observed_at": "2026-08-21T12:00:00Z",
        "supersedes_progress_id": None,
    }
    value.update(overrides)
    return {"value": value}


def test_parse_training_plan_activate_normalizes_strict_contract():
    parsed = _parse_plan()

    assert parsed.action is TrainingPlanAction.ACTIVATE
    assert parsed.expected_version is None
    assert parsed.plan_id is None
    assert parsed.normalized_payload == {
        "title": "Reduce early deaths",
        "objective": "Review positioning before minute 15",
        "metrics": [
            {
                "metric_key": "deaths_before_15",
                "direction": "decrease",
                "unit": "count",
                "baseline": 2.0,
                "target": 1.0,
                "stable_tolerance": 0.0,
            }
        ],
    }


@pytest.mark.parametrize("role", [RelationshipRole.OBSERVED])
def test_training_plan_is_self_only(role):
    with pytest.raises(TrainingContractError) as error:
        _parse_plan(role=role)
    assert error.value.reason_code == "training_requires_self_relationship"


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", " "),
        ("objective", "unsafe\ncontrol"),
        ("metrics", []),
        ("metrics", [{"metric_key": "bad metric", "direction": "decrease", "unit": "count"}]),
        ("metrics", [{"metric_key": "x", "direction": "sideways", "unit": "count"}]),
        ("metrics", [{"metric_key": "x", "direction": "decrease", "unit": "tokens"}]),
        ("metrics", [{"metric_key": "x", "direction": "decrease", "unit": "count", "baseline": True}]),
        ("metrics", [{"metric_key": "x", "direction": "decrease", "unit": "count", "target": float("inf")}]),
        ("metrics", [{"metric_key": "x", "direction": "decrease", "unit": "count", "stable_tolerance": -1.0}]),
    ],
)
def test_training_plan_rejects_invalid_typed_values(field, value):
    with pytest.raises(TrainingContractError) as error:
        _parse_plan(_plan_payload(**{field: value}))
    assert error.value.reason_code == "training_payload_invalid"


def test_training_plan_rejects_duplicate_metrics_and_extra_fields():
    duplicate = _plan_payload(
        metrics=[
            {"metric_key": "vision_score", "direction": "increase", "unit": "score"},
            {"metric_key": "vision_score", "direction": "increase", "unit": "score"},
        ]
    )
    with pytest.raises(TrainingContractError):
        _parse_plan(duplicate)
    with pytest.raises(TrainingContractError):
        _parse_plan({**_plan_payload(), "extra": "forbidden"})


@pytest.mark.parametrize("action", ["complete", "abandon"])
def test_training_plan_terminal_action_requires_plan_and_expected_version(action):
    parsed = _parse_plan(
        {
            "value": {"action": action, "plan_id": str(PLAN_ID)},
            "expected_version": 3,
        }
    )
    assert parsed.action.value == action
    assert parsed.plan_id == PLAN_ID
    assert parsed.expected_version == 3
    assert parsed.normalized_payload == {}

    with pytest.raises(TrainingContractError):
        _parse_plan({"value": {"action": action, "plan_id": str(PLAN_ID)}})


def test_parse_training_progress_normalizes_event_and_correction_reference():
    parsed = parse_training_progress_write(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.TRAINING_PROGRESS,
        operation=MemoryOperation.APPEND,
        relationship_role=RelationshipRole.SELF,
        proposal_payload=_progress_payload(supersedes_progress_id=str(PROGRESS_ID)),
    )

    assert parsed.plan_id == PLAN_ID
    assert parsed.metric_key == "deaths_before_15"
    assert parsed.metric_value == 1.0
    assert parsed.observed_at == datetime(2026, 8, 21, 12, tzinfo=timezone.utc)
    assert parsed.supersedes_progress_id == PROGRESS_ID


@pytest.mark.parametrize(
    "overrides",
    [
        {"metric_key": "unknown metric"},
        {"metric_value": True},
        {"metric_value": float("nan")},
        {"observed_at": "2026-08-21T12:00:00"},
        {"extra": "forbidden"},
    ],
)
def test_training_progress_rejects_unsafe_event_values(overrides):
    with pytest.raises(TrainingContractError) as error:
        parse_training_progress_write(
            target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.TRAINING_PROGRESS,
            operation=MemoryOperation.APPEND,
            relationship_role=RelationshipRole.SELF,
            proposal_payload=_progress_payload(**overrides),
        )
    assert error.value.reason_code == "training_payload_invalid"


def test_training_progress_rejects_observed_and_wrong_candidate_shape():
    with pytest.raises(TrainingContractError) as observed:
        parse_training_progress_write(
            target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.TRAINING_PROGRESS,
            operation=MemoryOperation.APPEND,
            relationship_role=RelationshipRole.OBSERVED,
            proposal_payload=_progress_payload(),
        )
    assert observed.value.reason_code == "training_requires_self_relationship"

    with pytest.raises(TrainingContractError) as wrong_operation:
        parse_training_progress_write(
            target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.TRAINING_PROGRESS,
            operation=MemoryOperation.SET,
            relationship_role=RelationshipRole.SELF,
            proposal_payload=_progress_payload(),
        )
    assert wrong_operation.value.reason_code == "training_candidate_shape_invalid"


@pytest.mark.parametrize(
    "direction,values,expected",
    [
        (MetricDirection.DECREASE, (2.0, 1.0), TrainingTrend.IMPROVING),
        (MetricDirection.DECREASE, (1.0, 2.0), TrainingTrend.DECLINING),
        (MetricDirection.INCREASE, (1.0, 2.0), TrainingTrend.IMPROVING),
        (MetricDirection.INCREASE, (2.0, 1.0), TrainingTrend.DECLINING),
        (MetricDirection.MAINTAIN, (1.0, 1.05), TrainingTrend.STABLE),
    ],
)
def test_compare_training_trend_is_deterministic(direction, values, expected):
    metric = MetricSpecification(
        metric_key="metric",
        direction=direction,
        unit=MetricUnit.SCORE,
        stable_tolerance=0.1,
    )
    result = compare_training_trend(metric=metric, values=values)
    assert result.trend is expected
    assert result.sample_count == 2
    assert result.previous_value == values[-2]
    assert result.current_value == values[-1]
    assert result.delta == pytest.approx(values[-1] - values[-2])
    assert not hasattr(result, "explanation")


def test_compare_training_trend_requires_two_finite_samples():
    metric = MetricSpecification(
        metric_key="metric",
        direction=MetricDirection.DECREASE,
        unit=MetricUnit.COUNT,
        stable_tolerance=0.0,
    )
    assert compare_training_trend(metric=metric, values=(1.0,)).trend is TrainingTrend.INSUFFICIENT_DATA
    with pytest.raises(TrainingContractError):
        compare_training_trend(metric=metric, values=(1.0, float("inf")))
