from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.memory.typed_models import TypedMemoryPage, TypedMemoryRecordView


TypedMemoryApiErrorCode: TypeAlias = Literal[
    "memory_scope_not_found",
    "service_unavailable",
]


class TypedMemoryApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TypedMemoryRecordResponse(TypedMemoryApiModel):
    schema_version: Literal["1.0"] = "1.0"
    record_id: UUID
    target_kind: Literal["owner_preference", "player_profile", "review_memory"]
    relationship_id: UUID | None
    relationship_role: Literal["self", "observed"] | None
    memory_key: str
    version: int
    status: Literal["active", "superseded", "retired"]
    payload: dict[str, Any]
    supersedes_record_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(cls, view: TypedMemoryRecordView) -> Self:
        if not isinstance(view, TypedMemoryRecordView):
            raise TypeError("view must be a TypedMemoryRecordView")
        return cls(**view.model_dump(mode="python"))


class TypedMemoryPageResponse(TypedMemoryApiModel):
    schema_version: Literal["1.0"] = "1.0"
    records: tuple[TypedMemoryRecordResponse, ...]

    @classmethod
    def from_page(cls, page: TypedMemoryPage) -> Self:
        if not isinstance(page, TypedMemoryPage):
            raise TypeError("page must be a TypedMemoryPage")
        return cls(
            records=tuple(
                TypedMemoryRecordResponse.from_view(item) for item in page.records
            )
        )


class TypedMemoryErrorResponse(TypedMemoryApiModel):
    code: TypedMemoryApiErrorCode


__all__ = [
    "TypedMemoryApiErrorCode",
    "TypedMemoryErrorResponse",
    "TypedMemoryPageResponse",
    "TypedMemoryRecordResponse",
]
