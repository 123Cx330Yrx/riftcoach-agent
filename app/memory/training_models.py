"""Pure contracts for 6B-7 Training Plans and Progress events.

No SQLAlchemy, filesystem, network, model, or Provider dependency belongs in
this module.  Pending Memory Candidates are the only Plan drafts; accepted
Candidates are parsed here before a transaction-owned writer persists them.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.memory.models import (
    CandidateDomainModel,
    CandidateKind,
    MemoryOperation,
    RelationshipRole,
    TargetScope,
)


MAX_PLAN_TITLE_LENGTH = 120
MAX_PLAN_OBJECTIVE_LENGTH = 1_000
MAX_PLAN_METRICS = 8
MAX_TRAINING_VERSION = 2_147_483_647
_METRIC_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


class TrainingContractError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class TrainingPlanAction(StrEnum):
    ACTIVATE = "activate"
    COMPLETE = "complete"
    ABANDON = "abandon"


class TrainingPlanStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class TrainingProgressStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class MetricDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"


class MetricUnit(StrEnum):
    COUNT = "count"
    RATIO = "ratio"
    PERCENT = "percent"
    SECONDS = "seconds"
    SCORE = "score"


class TrainingTrend(StrEnum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class MetricSpecification(CandidateDomainModel):
    metric_key: str = Field(min_length=1, max_length=64)
    direction: MetricDirection
    unit: MetricUnit
    baseline: float | None = None
    target: float | None = None
    stable_tolerance: float = Field(default=0.0, ge=0.0)

    @field_validator("metric_key")
    @classmethod
    def validate_metric_key(cls, value: str) -> str:
        if not _METRIC_PATTERN.fullmatch(value):
            raise ValueError("metric_key must be a safe identifier")
        return value

    @field_validator("baseline", "target", "stable_tolerance")
    @classmethod
    def validate_finite_number(cls, value: float | None) -> float | None:
        if value is not None and (isinstance(value, bool) or not math.isfinite(value)):
            raise ValueError("metric numbers must be finite")
        return value


class ActivateTrainingPlanValue(CandidateDomainModel):
    action: TrainingPlanAction
    title: str = Field(min_length=1, max_length=MAX_PLAN_TITLE_LENGTH)
    objective: str = Field(min_length=1, max_length=MAX_PLAN_OBJECTIVE_LENGTH)
    metrics: tuple[MetricSpecification, ...] = Field(
        min_length=1,
        max_length=MAX_PLAN_METRICS,
    )

    @field_validator("title", "objective")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.strip())
        if not normalized or any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError("training plan text is invalid")
        return normalized

    @field_validator("action")
    @classmethod
    def require_activate(cls, value: TrainingPlanAction) -> TrainingPlanAction:
        if value is not TrainingPlanAction.ACTIVATE:
            raise ValueError("activate payload requires activate action")
        return value

    @field_validator("metrics")
    @classmethod
    def require_unique_metrics(
        cls,
        value: tuple[MetricSpecification, ...],
    ) -> tuple[MetricSpecification, ...]:
        keys = [item.metric_key for item in value]
        if len(set(keys)) != len(keys):
            raise ValueError("training plan metric keys must be unique")
        return value


class TransitionTrainingPlanValue(CandidateDomainModel):
    action: TrainingPlanAction
    plan_id: UUID

    @field_validator("action")
    @classmethod
    def require_terminal_action(cls, value: TrainingPlanAction) -> TrainingPlanAction:
        if value not in {TrainingPlanAction.COMPLETE, TrainingPlanAction.ABANDON}:
            raise ValueError("transition payload requires a terminal action")
        return value


class TrainingPlanEnvelope(CandidateDomainModel):
    value: dict[str, Any]
    expected_version: int | None = Field(
        default=None,
        ge=1,
        le=MAX_TRAINING_VERSION,
    )

    @field_validator("expected_version")
    @classmethod
    def reject_bool_version(cls, value: int | None) -> int | None:
        if isinstance(value, bool):
            raise ValueError("expected_version must be an integer")
        return value


class ParsedTrainingPlanWrite(CandidateDomainModel):
    action: TrainingPlanAction
    expected_version: int | None
    plan_id: UUID | None
    normalized_payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_action_shape(self) -> Self:
        if self.action is TrainingPlanAction.ACTIVATE:
            if self.plan_id is not None or not self.normalized_payload:
                raise ValueError("activate write shape is invalid")
        elif self.plan_id is None or self.expected_version is None or self.normalized_payload:
            raise ValueError("terminal write shape is invalid")
        return self


class TrainingProgressValue(CandidateDomainModel):
    plan_id: UUID
    metric_key: str = Field(min_length=1, max_length=64)
    metric_value: float
    observed_at: datetime
    supersedes_progress_id: UUID | None = None

    @field_validator("metric_key")
    @classmethod
    def validate_metric_key(cls, value: str) -> str:
        if not _METRIC_PATTERN.fullmatch(value):
            raise ValueError("metric_key must be a safe identifier")
        return value

    @field_validator("metric_value")
    @classmethod
    def validate_value(cls, value: float) -> float:
        if isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("metric_value must be finite")
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class TrainingProgressEnvelope(CandidateDomainModel):
    value: dict[str, Any]


class ParsedTrainingProgressWrite(CandidateDomainModel):
    plan_id: UUID
    metric_key: str
    metric_value: float
    observed_at: datetime
    supersedes_progress_id: UUID | None = None


class TrainingTrendComparison(CandidateDomainModel):
    trend: TrainingTrend
    sample_count: int = Field(ge=0)
    previous_value: float | None = None
    current_value: float | None = None
    delta: float | None = None


class TrainingPlanView(CandidateDomainModel):
    schema_version: str = "1.0"
    plan_id: UUID
    relationship_id: UUID
    version: int = Field(ge=1, le=MAX_TRAINING_VERSION)
    status: TrainingPlanStatus
    payload: dict[str, Any]
    supersedes_plan_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        raw = dict(value)
        raw["action"] = TrainingPlanAction.ACTIVATE
        if isinstance(raw.get("metrics"), list):
            metrics = []
            for item in raw["metrics"]:
                if not isinstance(item, dict):
                    raise ValueError("training plan payload is invalid")
                metric = dict(item)
                metric["direction"] = MetricDirection(metric.get("direction"))
                metric["unit"] = MetricUnit(metric.get("unit"))
                metrics.append(metric)
            raw["metrics"] = tuple(metrics)
        parsed = ActivateTrainingPlanValue.model_validate(raw)
        return parsed.model_dump(mode="json", exclude={"action"}, exclude_none=True)

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("training timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_time_order(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        return self


class TrainingProgressView(CandidateDomainModel):
    schema_version: str = "1.0"
    progress_id: UUID
    plan_id: UUID
    relationship_id: UUID
    metric_key: str = Field(min_length=1, max_length=64)
    metric_value: float
    observed_at: datetime
    source_run_id: str = Field(min_length=1, max_length=128)
    source_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: TrainingProgressStatus
    supersedes_progress_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("metric_key")
    @classmethod
    def validate_metric_key(cls, value: str) -> str:
        if not _METRIC_PATTERN.fullmatch(value):
            raise ValueError("metric_key must be a safe identifier")
        return value

    @field_validator("metric_value")
    @classmethod
    def validate_metric_value(cls, value: float) -> float:
        if isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("metric_value must be finite")
        return value

    @field_validator("observed_at", "created_at", "updated_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("training timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)


class TrainingMetricTrendView(CandidateDomainModel):
    metric_key: str = Field(min_length=1, max_length=64)
    direction: MetricDirection
    comparison: TrainingTrendComparison


class TrainingPlanPage(CandidateDomainModel):
    plans: tuple[TrainingPlanView, ...] = Field(max_length=100)


class TrainingProgressPage(CandidateDomainModel):
    events: tuple[TrainingProgressView, ...] = Field(max_length=100)
    trends: tuple[TrainingMetricTrendView, ...] = Field(max_length=8)


def parse_training_plan_write(
    *,
    target_scope: TargetScope,
    candidate_kind: CandidateKind,
    operation: MemoryOperation,
    relationship_role: RelationshipRole,
    proposal_payload: object,
) -> ParsedTrainingPlanWrite:
    _validate_training_shape(
        target_scope=target_scope,
        candidate_kind=candidate_kind,
        expected_kind=CandidateKind.TRAINING_PLAN,
        operation=operation,
        expected_operation=MemoryOperation.SET,
        relationship_role=relationship_role,
    )
    try:
        envelope = TrainingPlanEnvelope.model_validate(proposal_payload)
        raw_action = envelope.value.get("action")
        action = TrainingPlanAction(raw_action)
        if action is TrainingPlanAction.ACTIVATE:
            value = dict(envelope.value)
            value["action"] = action
            raw_metrics = value.get("metrics")
            if isinstance(raw_metrics, list):
                metrics: list[object] = []
                for raw_metric in raw_metrics:
                    if not isinstance(raw_metric, dict):
                        metrics.append(raw_metric)
                        continue
                    metric = dict(raw_metric)
                    if "direction" in metric:
                        metric["direction"] = MetricDirection(metric["direction"])
                    if "unit" in metric:
                        metric["unit"] = MetricUnit(metric["unit"])
                    metrics.append(metric)
                value["metrics"] = tuple(metrics)
            parsed = ActivateTrainingPlanValue.model_validate(value)
            payload = parsed.model_dump(
                mode="json",
                exclude={"action"},
                exclude_none=True,
            )
            return ParsedTrainingPlanWrite(
                action=action,
                expected_version=envelope.expected_version,
                plan_id=None,
                normalized_payload=payload,
            )

        value = dict(envelope.value)
        value["action"] = action
        if "plan_id" in value and isinstance(value["plan_id"], str):
            value["plan_id"] = UUID(value["plan_id"])
        parsed_transition = TransitionTrainingPlanValue.model_validate(value)
        if envelope.expected_version is None:
            raise ValueError("terminal plan action requires expected_version")
        return ParsedTrainingPlanWrite(
            action=action,
            expected_version=envelope.expected_version,
            plan_id=parsed_transition.plan_id,
            normalized_payload={},
        )
    except (TypeError, ValueError) as exc:
        raise TrainingContractError("training_payload_invalid") from exc


def parse_training_progress_write(
    *,
    target_scope: TargetScope,
    candidate_kind: CandidateKind,
    operation: MemoryOperation,
    relationship_role: RelationshipRole,
    proposal_payload: object,
) -> ParsedTrainingProgressWrite:
    _validate_training_shape(
        target_scope=target_scope,
        candidate_kind=candidate_kind,
        expected_kind=CandidateKind.TRAINING_PROGRESS,
        operation=operation,
        expected_operation=MemoryOperation.APPEND,
        relationship_role=relationship_role,
    )
    try:
        envelope = TrainingProgressEnvelope.model_validate(proposal_payload)
        value = dict(envelope.value)
        for key in ("plan_id", "supersedes_progress_id"):
            if isinstance(value.get(key), str):
                value[key] = UUID(value[key])
        if isinstance(value.get("observed_at"), str):
            value["observed_at"] = datetime.fromisoformat(
                value["observed_at"].replace("Z", "+00:00")
            )
        parsed = TrainingProgressValue.model_validate(value)
        return ParsedTrainingProgressWrite(**parsed.model_dump(mode="python"))
    except (TypeError, ValueError) as exc:
        raise TrainingContractError("training_payload_invalid") from exc


def compare_training_trend(
    *,
    metric: MetricSpecification,
    values: tuple[float, ...],
) -> TrainingTrendComparison:
    if not isinstance(metric, MetricSpecification) or not isinstance(values, tuple):
        raise TypeError("metric and values must use training contract types")
    if any(isinstance(value, bool) or not math.isfinite(value) for value in values):
        raise TrainingContractError("training_metric_value_invalid")
    if len(values) < 2:
        return TrainingTrendComparison(
            trend=TrainingTrend.INSUFFICIENT_DATA,
            sample_count=len(values),
        )
    previous, current = values[-2:]
    delta = current - previous
    if abs(delta) <= metric.stable_tolerance:
        trend = TrainingTrend.STABLE
    elif metric.direction is MetricDirection.INCREASE:
        trend = TrainingTrend.IMPROVING if delta > 0 else TrainingTrend.DECLINING
    elif metric.direction is MetricDirection.DECREASE:
        trend = TrainingTrend.IMPROVING if delta < 0 else TrainingTrend.DECLINING
    else:
        trend = TrainingTrend.DECLINING
    return TrainingTrendComparison(
        trend=trend,
        sample_count=len(values),
        previous_value=previous,
        current_value=current,
        delta=delta,
    )


def _validate_training_shape(
    *,
    target_scope: TargetScope,
    candidate_kind: CandidateKind,
    expected_kind: CandidateKind,
    operation: MemoryOperation,
    expected_operation: MemoryOperation,
    relationship_role: RelationshipRole,
) -> None:
    if relationship_role is not RelationshipRole.SELF:
        raise TrainingContractError("training_requires_self_relationship")
    if (
        target_scope is not TargetScope.OWNER_PLAYER
        or candidate_kind is not expected_kind
        or operation is not expected_operation
    ):
        raise TrainingContractError("training_candidate_shape_invalid")


__all__ = [
    "MetricDirection",
    "MetricSpecification",
    "MetricUnit",
    "ParsedTrainingPlanWrite",
    "ParsedTrainingProgressWrite",
    "TrainingContractError",
    "TrainingPlanAction",
    "TrainingPlanPage",
    "TrainingPlanStatus",
    "TrainingPlanView",
    "TrainingMetricTrendView",
    "TrainingProgressPage",
    "TrainingProgressStatus",
    "TrainingProgressView",
    "TrainingTrend",
    "TrainingTrendComparison",
    "compare_training_trend",
    "parse_training_plan_write",
    "parse_training_progress_write",
]
