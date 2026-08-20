from __future__ import annotations

from uuid import UUID

from app.memory.typed_models import TypedMemoryPage, TypedMemoryRecordView
from app.memory.typed_ports import TypedMemoryQueryRepository


class TypedMemoryQueryServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        if code not in {"memory_scope_not_found", "service_unavailable"}:
            raise ValueError("typed memory query error code is not allowlisted")
        self.code = code
        super().__init__(code)


class TypedMemoryQueryService:
    def __init__(self, repository: TypedMemoryQueryRepository) -> None:
        for method_name in ("list_preferences", "list_profile", "list_reviews"):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        self._repository = repository

    def preferences(
        self,
        *,
        owner_id: str,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage:
        records = self._call(
            "list_preferences",
            owner_id=owner_id,
            include_history=include_history,
            limit=limit,
        )
        if records is None:
            raise TypedMemoryQueryServiceError("service_unavailable")
        return TypedMemoryPage(records=records)

    def profile(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage:
        records = self._call(
            "list_profile",
            owner_id=owner_id,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
        )
        if records is None:
            raise TypedMemoryQueryServiceError("memory_scope_not_found")
        return TypedMemoryPage(records=records)

    def reviews(
        self,
        *,
        owner_id: str,
        relationship_id: UUID,
        include_history: bool,
        limit: int,
    ) -> TypedMemoryPage:
        records = self._call(
            "list_reviews",
            owner_id=owner_id,
            relationship_id=relationship_id,
            include_history=include_history,
            limit=limit,
        )
        if records is None:
            raise TypedMemoryQueryServiceError("memory_scope_not_found")
        return TypedMemoryPage(records=records)

    def _call(self, method_name: str, **kwargs):
        try:
            records = getattr(self._repository, method_name)(**kwargs)
        except Exception:
            raise TypedMemoryQueryServiceError("service_unavailable") from None
        if records is not None and (
            not isinstance(records, tuple)
            or any(not isinstance(item, TypedMemoryRecordView) for item in records)
        ):
            raise TypedMemoryQueryServiceError("service_unavailable")
        return records


__all__ = ["TypedMemoryQueryService", "TypedMemoryQueryServiceError"]
