"""Strict domain contracts for the 6B-6 typed memory targets.

This module deliberately has no SQLAlchemy, filesystem, network, model, or
provider dependency.  It answers only: "is this Candidate proposal a valid
Preference/Profile/Review Memory write, and what normalized value would be
stored?"  Persistence and transaction semantics live in the later Repository
task.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator, model_validator
from typing_extensions import Annotated

from app.memory.models import (
    CandidateKind,
    CandidateDomainModel,
    MemoryOperation,
    RelationshipRole,
    TargetScope,
)


MAX_TYPED_VALUE_BYTES = 4 * 1024
MAX_CHAMPION_POOL_SIZE = 20
MAX_REVIEW_TEXT_LENGTH = 2_000
MAX_TREND_METRIC_LENGTH = 64
MAX_VERSION = 2_147_483_647

_SAFE_METRIC_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")

SafeMetric = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=MAX_TREND_METRIC_LENGTH,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$",
    ),
]
ChampionName = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9 .'_-]{0,31}$",
    ),
]


class TypedMemoryContractError(ValueError):
    """Safe, allowlisted failure for a typed memory proposal."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class MemoryTargetKind(StrEnum):
    OWNER_PREFERENCE = "owner_preference"
    PLAYER_PROFILE = "player_profile"
    REVIEW_MEMORY = "review_memory"


class MemoryTargetStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class MainRole(StrEnum):
    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MIDDLE = "MIDDLE"
    BOTTOM = "BOTTOM"
    UTILITY = "UTILITY"
    UNKNOWN = "UNKNOWN"


class TrendDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class MemoryWriteEnvelope(CandidateDomainModel):
    """The common proposal envelope consumed by 6B-6 materializers."""

    value: Any
    expected_version: int | None = Field(default=None, ge=1, le=MAX_VERSION)

    @field_validator("expected_version")
    @classmethod
    def reject_bool_version(cls, value: int | None) -> int | None:
        if isinstance(value, bool):
            raise ValueError("expected_version must be an integer")
        return value


class ReportLanguagePayload(CandidateDomainModel):
    value: Literal["zh-CN", "en-US"]


class MainRolePayload(CandidateDomainModel):
    value: MainRole


class ChampionPoolPayload(CandidateDomainModel):
    value: list[ChampionName] = Field(
        min_length=1,
        max_length=MAX_CHAMPION_POOL_SIZE,
    )

    @field_validator("value")
    @classmethod
    def validate_unique_champions(cls, value: list[str]) -> list[str]:
        if len({item.casefold() for item in value}) != len(value):
            raise ValueError("champion_pool must not contain duplicates")
        return value


class ReviewSummaryPayload(CandidateDomainModel):
    text: str = Field(min_length=1, max_length=MAX_REVIEW_TEXT_LENGTH)
    metrics: dict[SafeMetric, float] | None = Field(default=None, max_length=20)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_text(value, field_name="review_summary.text")

    @field_validator("metrics")
    @classmethod
    def validate_metrics(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is not None and any(
            isinstance(item, bool) or not math.isfinite(item)
            for item in value.values()
        ):
            raise ValueError("review_summary.metrics must be finite")
        return value


class ObservationNotePayload(CandidateDomainModel):
    text: str = Field(min_length=1, max_length=MAX_REVIEW_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_text(value, field_name="observation_note.text")


class PublicTrendPayload(CandidateDomainModel):
    metric: SafeMetric
    direction: TrendDirection
    value: float | None = None

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, value: str) -> str:
        if not _SAFE_METRIC_PATTERN.fullmatch(value):
            raise ValueError("public_trend.metric must be an allowlisted identifier")
        return value

    @field_validator("value")
    @classmethod
    def validate_finite_value(cls, value: float | None) -> float | None:
        if value is not None and (isinstance(value, bool) or not math.isfinite(value)):
            raise ValueError("public_trend.value must be finite")
        return value


class ParsedTypedMemoryWrite(CandidateDomainModel):
    """Normalized result passed from pure contract code to a materializer."""

    target_kind: MemoryTargetKind
    memory_key: str
    operation: MemoryOperation
    relationship_role: RelationshipRole
    expected_version: int | None
    normalized_payload: dict[str, Any]

    @field_validator("normalized_payload")
    @classmethod
    def validate_payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        # Reuse the Candidate JSON rules and impose a smaller target-value bound.
        from app.memory.models import canonical_payload_bytes

        encoded = canonical_payload_bytes(value)
        if len(encoded) > MAX_TYPED_VALUE_BYTES:
            raise ValueError("typed memory value exceeds the 4 KiB bound")
        return value


class TypedMemoryRecordView(CandidateDomainModel):
    schema_version: Literal["1.0"] = "1.0"
    record_id: UUID
    target_kind: MemoryTargetKind
    relationship_id: UUID | None = None
    relationship_role: RelationshipRole | None = None
    memory_key: str
    version: int = Field(ge=1, le=MAX_VERSION)
    status: MemoryTargetStatus
    payload: dict[str, Any]
    supersedes_record_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("payload")
    @classmethod
    def validate_public_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        from app.memory.models import canonical_payload_bytes

        encoded = canonical_payload_bytes(value)
        if len(encoded) > MAX_TYPED_VALUE_BYTES:
            raise ValueError("typed memory value exceeds the 4 KiB bound")
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("typed memory timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_scope_shape(self) -> Self:
        is_preference = self.target_kind is MemoryTargetKind.OWNER_PREFERENCE
        relation_fields_present = (
            self.relationship_id is not None and self.relationship_role is not None
        )
        if is_preference and (
            self.relationship_id is not None or self.relationship_role is not None
        ):
            raise ValueError("owner preference view must omit player relationship")
        if not is_preference and not relation_fields_present:
            raise ValueError("player-scoped memory view requires relationship")
        if self.updated_at < self.created_at:
            raise ValueError("typed memory updated_at must not precede created_at")
        return self


class TypedMemoryPage(CandidateDomainModel):
    records: tuple[TypedMemoryRecordView, ...] = Field(max_length=100)


def parse_typed_memory_write(
    *,
    target_scope: TargetScope,
    candidate_kind: CandidateKind,
    memory_key: str,
    operation: MemoryOperation,
    relationship_role: RelationshipRole,
    proposal_payload: object,
) -> ParsedTypedMemoryWrite:
    """Validate one Candidate proposal and return its normalized target value."""

    envelope = _parse_envelope(proposal_payload)
    target_kind = _validate_shape(
        target_scope=target_scope,
        candidate_kind=candidate_kind,
        memory_key=memory_key,
        operation=operation,
        relationship_role=relationship_role,
    )
    payload_model = _payload_model_for_key(
        target_kind=target_kind,
        memory_key=memory_key,
        relationship_role=relationship_role,
        value=envelope.value,
    )
    normalized = payload_model.model_dump(mode="json", exclude_none=True)
    try:
        return ParsedTypedMemoryWrite(
            target_kind=target_kind,
            memory_key=memory_key,
            operation=operation,
            relationship_role=relationship_role,
            expected_version=envelope.expected_version,
            normalized_payload=normalized,
        )
    except ValueError as exc:
        raise TypedMemoryContractError("typed_payload_invalid") from exc


def _parse_envelope(proposal_payload: object) -> MemoryWriteEnvelope:
    try:
        return MemoryWriteEnvelope.model_validate(proposal_payload)
    except ValueError as exc:
        raise TypedMemoryContractError("typed_envelope_invalid") from exc


def _validate_shape(
    *,
    target_scope: TargetScope,
    candidate_kind: CandidateKind,
    memory_key: str,
    operation: MemoryOperation,
    relationship_role: RelationshipRole,
) -> MemoryTargetKind:
    if candidate_kind is CandidateKind.OWNER_PREFERENCE:
        if target_scope is not TargetScope.OWNER_GLOBAL:
            raise TypedMemoryContractError("typed_scope_kind_mismatch")
        if relationship_role is not RelationshipRole.SELF:
            raise TypedMemoryContractError("preference_requires_self_relationship")
        if memory_key != "report_language":
            raise TypedMemoryContractError("typed_memory_key_unknown")
        if operation is not MemoryOperation.SET:
            raise TypedMemoryContractError("preference_key_or_operation_forbidden")
        return MemoryTargetKind.OWNER_PREFERENCE

    if target_scope is not TargetScope.OWNER_PLAYER:
        raise TypedMemoryContractError("typed_scope_kind_mismatch")

    if candidate_kind is CandidateKind.PLAYER_PROFILE:
        if relationship_role is not RelationshipRole.SELF:
            raise TypedMemoryContractError("profile_requires_self_relationship")
        if memory_key not in {"main_role", "champion_pool"}:
            raise TypedMemoryContractError("typed_memory_key_unknown")
        if operation is not MemoryOperation.SET:
            raise TypedMemoryContractError("profile_key_or_operation_forbidden")
        return MemoryTargetKind.PLAYER_PROFILE

    if candidate_kind is CandidateKind.REVIEW_MEMORY:
        if operation is not MemoryOperation.APPEND:
            raise TypedMemoryContractError("review_memory_requires_append")
        if memory_key not in {"review_summary", "observation_note", "public_trend"}:
            raise TypedMemoryContractError("review_memory_key_forbidden")
        if relationship_role is RelationshipRole.OBSERVED and memory_key not in {
            "observation_note",
            "public_trend",
        }:
            raise TypedMemoryContractError("observed_review_key_forbidden")
        return MemoryTargetKind.REVIEW_MEMORY

    raise TypedMemoryContractError("typed_candidate_kind_forbidden")


def _payload_model_for_key(
    *,
    target_kind: MemoryTargetKind,
    memory_key: str,
    relationship_role: RelationshipRole,
    value: object,
) -> CandidateDomainModel:
    del target_kind
    if memory_key == "report_language":
        model_type = ReportLanguagePayload
        value_for_model = {"value": value}
    elif memory_key == "main_role":
        model_type = MainRolePayload
        value_for_model = {"value": _enum_value(MainRole, value)}
    elif memory_key == "champion_pool":
        model_type = ChampionPoolPayload
        value_for_model = {"value": value}
    elif memory_key == "review_summary":
        if relationship_role is RelationshipRole.OBSERVED:
            raise TypedMemoryContractError("observed_review_key_forbidden")
        model_type = ReviewSummaryPayload
        value_for_model = value
    elif memory_key == "observation_note":
        model_type = ObservationNotePayload
        value_for_model = value
    elif memory_key == "public_trend":
        model_type = PublicTrendPayload
        if isinstance(value, dict):
            value_for_model = dict(value)
            if "direction" in value_for_model:
                value_for_model["direction"] = _enum_value(
                    TrendDirection,
                    value_for_model["direction"],
                )
        else:
            value_for_model = value
    else:
        raise TypedMemoryContractError("typed_memory_key_unknown")
    try:
        return model_type.model_validate(value_for_model)
    except ValueError as exc:
        raise TypedMemoryContractError("typed_payload_invalid") from exc


def _enum_value(enum_type: type[StrEnum], value: object) -> StrEnum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise TypedMemoryContractError("typed_payload_invalid") from exc


def _validate_text(value: str, *, field_name: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip())
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        raise ValueError(f"{field_name} must not contain control characters")
    return normalized


__all__ = [
    "ChampionPoolPayload",
    "ChampionName",
    "MAX_CHAMPION_POOL_SIZE",
    "MAX_REVIEW_TEXT_LENGTH",
    "MAX_TYPED_VALUE_BYTES",
    "MainRole",
    "MainRolePayload",
    "MemoryTargetKind",
    "MemoryTargetStatus",
    "MemoryWriteEnvelope",
    "ObservationNotePayload",
    "ParsedTypedMemoryWrite",
    "PublicTrendPayload",
    "ReportLanguagePayload",
    "ReviewSummaryPayload",
    "TrendDirection",
    "TypedMemoryContractError",
    "TypedMemoryPage",
    "TypedMemoryRecordView",
    "parse_typed_memory_write",
]
