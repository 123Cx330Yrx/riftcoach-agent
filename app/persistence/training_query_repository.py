from __future__ import annotations

import re
from collections.abc import Callable
from uuid import UUID

import sqlalchemy as sa
from pydantic import TypeAdapter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.memory.models import OwnerId
from app.memory.training_models import (
    MetricDirection,
    MetricSpecification,
    MetricUnit,
    TrainingMetricTrendView,
    TrainingPlanStatus,
    TrainingPlanView,
    TrainingProgressPage,
    TrainingProgressStatus,
    TrainingProgressView,
    compare_training_trend,
)
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord


SessionFactory = Callable[[], Session]
_OWNER = TypeAdapter(OwnerId)
_METRIC = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


class TrainingQueryRepositoryError(RuntimeError):
    pass


class PostgresTrainingQueryRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable")
        self._session_factory = session_factory

    def list_plans(self, *, owner_id, relationship_id, include_history, limit):
        owner, bounded = _validate(owner_id, relationship_id, limit)
        try:
            with self._session_factory() as session:
                with session.begin():
                    if _self_relationship(session, owner, relationship_id) is None:
                        return None
                    statement = sa.select(TrainingPlanRecord).where(
                        TrainingPlanRecord.owner_id == owner,
                        TrainingPlanRecord.relationship_id == relationship_id,
                    )
                    if not include_history:
                        statement = statement.where(TrainingPlanRecord.status == "active")
                    rows = tuple(
                        session.scalars(
                            statement.order_by(TrainingPlanRecord.version.desc()).limit(bounded)
                        )
                    )
                return tuple(_plan_view(row) for row in rows)
        except SQLAlchemyError:
            raise TrainingQueryRepositoryError("training_query_unavailable") from None
        except (TypeError, ValueError):
            raise TrainingQueryRepositoryError("training_query_integrity_failed") from None

    def list_progress(
        self,
        *,
        owner_id,
        relationship_id,
        metric_key,
        include_history,
        limit,
    ):
        owner, bounded = _validate(owner_id, relationship_id, limit)
        if metric_key is not None and (
            not isinstance(metric_key, str) or not _METRIC.fullmatch(metric_key)
        ):
            raise TypeError("metric_key is invalid")
        try:
            with self._session_factory() as session:
                with session.begin():
                    if _self_relationship(session, owner, relationship_id) is None:
                        return None
                    plan = session.scalar(
                        sa.select(TrainingPlanRecord).where(
                            TrainingPlanRecord.owner_id == owner,
                            TrainingPlanRecord.relationship_id == relationship_id,
                            TrainingPlanRecord.status == "active",
                        )
                    )
                    if plan is None:
                        return TrainingProgressPage(events=(), trends=())
                    statement = sa.select(TrainingProgressRecord).where(
                        TrainingProgressRecord.owner_id == owner,
                        TrainingProgressRecord.relationship_id == relationship_id,
                        TrainingProgressRecord.plan_id == plan.plan_id,
                    )
                    if metric_key is not None:
                        statement = statement.where(TrainingProgressRecord.metric_key == metric_key)
                    if not include_history:
                        statement = statement.where(TrainingProgressRecord.status == "active")
                    rows = tuple(
                        session.scalars(
                            statement.order_by(
                                TrainingProgressRecord.observed_at.desc(),
                                TrainingProgressRecord.created_at.desc(),
                                TrainingProgressRecord.progress_id.desc(),
                            ).limit(bounded)
                        )
                    )
                events = tuple(_progress_view(row) for row in rows)
                return TrainingProgressPage(
                    events=events,
                    trends=_trends(plan.payload, events),
                )
        except SQLAlchemyError:
            raise TrainingQueryRepositoryError("training_query_unavailable") from None
        except (TypeError, ValueError):
            raise TrainingQueryRepositoryError("training_query_integrity_failed") from None


def _validate(owner_id: str, relationship_id: UUID, limit: int) -> tuple[str, int]:
    try:
        owner = _OWNER.validate_python(owner_id, strict=True)
    except ValueError:
        raise TypeError("owner_id is invalid") from None
    if not isinstance(relationship_id, UUID):
        raise TypeError("relationship_id must be UUID")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise TypeError("limit must be between 1 and 100")
    return owner, limit


def _self_relationship(session: Session, owner_id: str, relationship_id: UUID):
    return session.scalar(
        sa.select(OwnerPlayerRelationshipRecord).where(
            OwnerPlayerRelationshipRecord.owner_id == owner_id,
            OwnerPlayerRelationshipRecord.relationship_id == relationship_id,
            OwnerPlayerRelationshipRecord.relationship_role == "self",
            OwnerPlayerRelationshipRecord.status == "active",
        )
    )


def _plan_view(row: TrainingPlanRecord) -> TrainingPlanView:
    return TrainingPlanView(
        plan_id=row.plan_id,
        relationship_id=row.relationship_id,
        version=row.version,
        status=TrainingPlanStatus(row.status),
        payload=row.payload,
        supersedes_plan_id=row.supersedes_plan_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _progress_view(row: TrainingProgressRecord) -> TrainingProgressView:
    return TrainingProgressView(
        progress_id=row.progress_id,
        plan_id=row.plan_id,
        relationship_id=row.relationship_id,
        metric_key=row.metric_key,
        metric_value=row.metric_value,
        observed_at=row.observed_at,
        source_run_id=row.source_run_id,
        source_artifact_sha256=row.source_artifact_sha256,
        status=TrainingProgressStatus(row.status),
        supersedes_progress_id=row.supersedes_progress_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _trends(payload: dict, events: tuple[TrainingProgressView, ...]):
    raw_metrics = payload.get("metrics") if isinstance(payload, dict) else None
    if not isinstance(raw_metrics, list):
        raise ValueError("training plan metrics are invalid")
    metrics = []
    for item in raw_metrics:
        raw = dict(item)
        raw["direction"] = MetricDirection(raw.get("direction"))
        raw["unit"] = MetricUnit(raw.get("unit"))
        metrics.append(MetricSpecification.model_validate(raw))
    by_key = {metric.metric_key: metric for metric in metrics}
    result = []
    for key in sorted({event.metric_key for event in events}):
        metric = by_key.get(key)
        if metric is None:
            raise ValueError("progress metric is absent from Plan")
        values = tuple(
            event.metric_value
            for event in reversed(events)
            if event.metric_key == key and event.status is TrainingProgressStatus.ACTIVE
        )
        result.append(
            TrainingMetricTrendView(
                metric_key=key,
                direction=metric.direction,
                comparison=compare_training_trend(metric=metric, values=values),
            )
        )
    return tuple(result)


__all__ = ["PostgresTrainingQueryRepository", "TrainingQueryRepositoryError"]
