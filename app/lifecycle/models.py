from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)


OwnerId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$",
    ),
]
IdempotencyKey = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@|+-]{0,127}$",
    ),
]
SafeCode = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$",
    ),
]
_SAFE_RECORD_KIND = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_FORBIDDEN_EXPORT_KEYS = frozenset(
    {
        "puuid",
        "api_key",
        "prompt",
        "provider_body",
        "tool_body",
        "exception",
        "traceback",
    }
)


class LifecycleModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class OwnerDataDeleteScope(StrEnum):
    CONVERSATION_ONLY = "conversation_only"
    CONVERSATION_AND_DERIVED_MEMORY = "conversation_and_derived_memory"
    RELATIONSHIP_PRIVATE_DATA = "relationship_private_data"


class OwnerDataDeletionStatus(StrEnum):
    CLEANUP_PENDING = "cleanup_pending"
    COMPLETE = "complete"


class OwnerDataDeleteCommand(LifecycleModel):
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    scope: OwnerDataDeleteScope
    conversation_id: UUID | None = None
    relationship_id: UUID | None = None
    requested_at: datetime

    @field_validator("requested_at")
    @classmethod
    def normalize_requested_at(cls, value: datetime) -> datetime:
        return _aware_utc(value, "requested_at")

    @model_validator(mode="after")
    def validate_target_shape(self) -> Self:
        conversation_scope = self.scope in {
            OwnerDataDeleteScope.CONVERSATION_ONLY,
            OwnerDataDeleteScope.CONVERSATION_AND_DERIVED_MEMORY,
        }
        if conversation_scope:
            if self.conversation_id is None or self.relationship_id is not None:
                raise ValueError("conversation delete scope requires only conversation_id")
        elif self.conversation_id is not None or self.relationship_id is None:
            raise ValueError("relationship delete scope requires only relationship_id")
        return self


class OwnerDataAffectedCounts(LifecycleModel):
    relationships: int = Field(default=0, ge=0, le=1_000_000)
    conversations: int = Field(default=0, ge=0, le=1_000_000)
    messages: int = Field(default=0, ge=0, le=1_000_000)
    candidates: int = Field(default=0, ge=0, le=1_000_000)
    typed_memories: int = Field(default=0, ge=0, le=1_000_000)
    training_plans: int = Field(default=0, ge=0, le=1_000_000)
    training_progress: int = Field(default=0, ge=0, le=1_000_000)

    @property
    def total(self) -> int:
        return sum(
            (
                self.relationships,
                self.conversations,
                self.messages,
                self.candidates,
                self.typed_memories,
                self.training_plans,
                self.training_progress,
            )
        )


class OwnerDataDeletionMarker(LifecycleModel):
    schema_version: Literal["1.0"] = "1.0"
    marker_id: UUID
    owner_id: OwnerId
    idempotency_key: IdempotencyKey
    scope: OwnerDataDeleteScope
    conversation_id: UUID | None = None
    relationship_id: UUID | None = None
    affected: OwnerDataAffectedCounts
    status: OwnerDataDeletionStatus
    safe_reason: SafeCode | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @field_validator("created_at", "updated_at", "completed_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware_utc(value, "timestamp")

    @model_validator(mode="after")
    def validate_marker_shape(self) -> Self:
        conversation_scope = self.scope in {
            OwnerDataDeleteScope.CONVERSATION_ONLY,
            OwnerDataDeleteScope.CONVERSATION_AND_DERIVED_MEMORY,
        }
        if conversation_scope:
            if self.conversation_id is None or self.relationship_id is not None:
                raise ValueError("conversation marker target is invalid")
        elif self.conversation_id is not None or self.relationship_id is None:
            raise ValueError("relationship marker target is invalid")
        if self.updated_at < self.created_at:
            raise ValueError("marker updated_at precedes created_at")
        if self.status is OwnerDataDeletionStatus.COMPLETE:
            if self.safe_reason is not None or self.completed_at is None:
                raise ValueError("complete marker shape is invalid")
            if self.completed_at < self.created_at:
                raise ValueError("marker completed_at precedes created_at")
        elif self.completed_at is not None:
            raise ValueError("pending marker cannot be completed")
        return self

    @property
    def cleanup_pending(self) -> bool:
        return self.status is OwnerDataDeletionStatus.CLEANUP_PENDING


class OwnerDataExportRecord(LifecycleModel):
    record_kind: str
    record_id: UUID
    conversation_id: UUID | None = None
    relationship_id: UUID | None = None
    relationship_role: Literal["self", "observed"] | None = None
    status: str
    data: dict[str, JsonValue]

    @field_validator("record_kind")
    @classmethod
    def validate_record_kind(cls, value: str) -> str:
        if not _SAFE_RECORD_KIND.fullmatch(value):
            raise ValueError("record_kind must be a safe identifier")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if not value or len(value) > 64 or not _SAFE_RECORD_KIND.fullmatch(value):
            raise ValueError("status must be a safe identifier")
        return value

    @field_validator("data")
    @classmethod
    def validate_safe_data(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if len(value) > 64:
            raise ValueError("export record has too many fields")
        _reject_forbidden_export_keys(value)
        return value


class OwnerDataExportSection(LifecycleModel):
    name: str
    records: tuple[OwnerDataExportRecord, ...] = Field(max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _SAFE_RECORD_KIND.fullmatch(value):
            raise ValueError("section name must be a safe identifier")
        return value


class OwnerDataExport(LifecycleModel):
    schema_version: Literal["1.0"] = "1.0"
    owner_id: OwnerId
    generated_at: datetime
    policy_version: SafeCode
    sections: tuple[OwnerDataExportSection, ...] = Field(max_length=16)
    total_record_count: int = Field(ge=0, le=8_000)

    @field_validator("generated_at")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        return _aware_utc(value, "generated_at")

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        names = tuple(section.name for section in self.sections)
        if len(set(names)) != len(names):
            raise ValueError("export section names must be unique")
        if sum(len(section.records) for section in self.sections) != self.total_record_count:
            raise ValueError("export total_record_count is inconsistent")
        return self


class OwnerDataRetentionSummary(LifecycleModel):
    schema_version: Literal["1.0"] = "1.0"
    evaluated_at: datetime
    batch_size: int = Field(ge=1, le=1_000)
    expired_candidates: int = Field(ge=0, le=1_000)
    hidden_records: int = Field(ge=0, le=7_000)

    @field_validator("evaluated_at")
    @classmethod
    def normalize_evaluated_at(cls, value: datetime) -> datetime:
        return _aware_utc(value, "evaluated_at")


class OwnerDataPurgeSummary(LifecycleModel):
    schema_version: Literal["1.0"] = "1.0"
    evaluated_at: datetime
    batch_size: int = Field(ge=1, le=1_000)
    purged_records: int = Field(ge=0, le=7_000)
    blocked_records: int = Field(ge=0, le=7_000)

    @field_validator("evaluated_at")
    @classmethod
    def normalize_evaluated_at(cls, value: datetime) -> datetime:
        return _aware_utc(value, "evaluated_at")


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _reject_forbidden_export_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).casefold() in _FORBIDDEN_EXPORT_KEYS:
                raise ValueError("export data contains a forbidden field")
            _reject_forbidden_export_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_export_keys(nested)


__all__ = [
    "OwnerDataAffectedCounts",
    "OwnerDataDeleteCommand",
    "OwnerDataDeleteScope",
    "OwnerDataDeletionMarker",
    "OwnerDataDeletionStatus",
    "OwnerDataExport",
    "OwnerDataExportRecord",
    "OwnerDataExportSection",
    "OwnerDataPurgeSummary",
    "OwnerDataRetentionSummary",
]
