from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.memory.typed_models import TypedMemoryPage, TypedMemoryRecordView


class TypedMemoryQueryRepository(Protocol):
    def list_preferences(
        self,
        *,
        owner_id: str,
        include_history: bool,
        limit: int,
    ) -> tuple[TypedMemoryRecordView, ...]: ...

    def list_profile(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> tuple[TypedMemoryRecordView, ...] | None: ...

    def list_reviews(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> tuple[TypedMemoryRecordView, ...] | None: ...


class TypedMemoryQueryServicePort(Protocol):
    def preferences(
        self,
        *,
        owner_id: str,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage: ...

    def profile(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage: ...

    def reviews(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage: ...


__all__ = ["TypedMemoryQueryRepository", "TypedMemoryQueryServicePort"]
