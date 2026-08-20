from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.lifecycle.models import (
    OwnerDataDeleteScope,
    OwnerDataDeletionMarker,
    OwnerDataExport,
    OwnerDataExportSection,
    OwnerDataAffectedCounts,
)


LifecycleApiErrorCode: TypeAlias = Literal[
    "deletion_not_found",
    "idempotency_conflict",
    "export_too_large",
    "lifecycle_unavailable",
    "lifecycle_integrity_failed",
]


class LifecycleApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class OwnerDataExportResponse(LifecycleApiModel):
    schema_version: Literal["1.0"] = "1.0"
    owner_id: str
    generated_at: datetime
    policy_version: str
    sections: tuple[OwnerDataExportSection, ...]
    total_record_count: int

    @classmethod
    def from_export(cls, export: OwnerDataExport) -> "OwnerDataExportResponse":
        if not isinstance(export, OwnerDataExport):
            raise TypeError("export must be OwnerDataExport")
        return cls(**export.model_dump(mode="python"))


class OwnerDataDeleteRequest(LifecycleApiModel):
    scope: Literal[
        "conversation_only",
        "conversation_and_derived_memory",
        "relationship_private_data",
    ]
    conversation_id: UUID | None = None
    relationship_id: UUID | None = None

    @field_validator("conversation_id", "relationship_id", mode="before")
    @classmethod
    def parse_json_uuid(cls, value: object) -> object:
        if value is None or isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                pass
        raise ValueError("lifecycle target must be a UUID")


class OwnerDataDeletionResponse(LifecycleApiModel):
    schema_version: Literal["1.0"] = "1.0"
    marker_id: UUID
    owner_id: str
    idempotency_key: str
    scope: OwnerDataDeleteScope
    conversation_id: UUID | None
    relationship_id: UUID | None
    affected: OwnerDataAffectedCounts
    status: Literal["cleanup_pending", "complete"]
    safe_reason: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_marker(cls, marker: OwnerDataDeletionMarker) -> "OwnerDataDeletionResponse":
        if not isinstance(marker, OwnerDataDeletionMarker):
            raise TypeError("marker must be OwnerDataDeletionMarker")
        return cls(**marker.model_dump(mode="python"))


class LifecycleErrorResponse(LifecycleApiModel):
    code: LifecycleApiErrorCode


__all__ = [
    "LifecycleApiErrorCode",
    "LifecycleErrorResponse",
    "OwnerDataDeleteRequest",
    "OwnerDataDeletionResponse",
    "OwnerDataExportResponse",
]
