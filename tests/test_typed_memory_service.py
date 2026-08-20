from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.memory.models import RelationshipRole
from app.memory.typed_models import (
    MemoryTargetKind,
    MemoryTargetStatus,
    TypedMemoryPage,
    TypedMemoryRecordView,
)
from app.memory.typed_service import TypedMemoryQueryService, TypedMemoryQueryServiceError


NOW = datetime(2026, 8, 20, 18, 0, tzinfo=timezone.utc)
RELATIONSHIP_ID = UUID("93000000-0000-4000-8000-000000000001")


def preference() -> TypedMemoryRecordView:
    return TypedMemoryRecordView(
        record_id=UUID("93000000-0000-4000-8000-000000000002"),
        target_kind=MemoryTargetKind.OWNER_PREFERENCE,
        memory_key="report_language",
        version=1,
        status=MemoryTargetStatus.ACTIVE,
        payload={"value": "zh-CN"},
        created_at=NOW,
        updated_at=NOW,
    )


def profile() -> TypedMemoryRecordView:
    return TypedMemoryRecordView(
        record_id=UUID("93000000-0000-4000-8000-000000000003"),
        target_kind=MemoryTargetKind.PLAYER_PROFILE,
        relationship_id=RELATIONSHIP_ID,
        relationship_role=RelationshipRole.SELF,
        memory_key="main_role",
        version=1,
        status=MemoryTargetStatus.ACTIVE,
        payload={"value": "TOP"},
        created_at=NOW,
        updated_at=NOW,
    )


class FakeRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.preference_result = (preference(),)
        self.profile_result = (profile(),)
        self.review_result = ()
        self.failure: Exception | None = None

    def _result(self, name, kwargs, result):
        self.calls.append((name, kwargs))
        if self.failure is not None:
            raise self.failure
        return result

    def list_preferences(self, **kwargs):
        return self._result("preferences", kwargs, self.preference_result)

    def list_profile(self, **kwargs):
        return self._result("profile", kwargs, self.profile_result)

    def list_reviews(self, **kwargs):
        return self._result("reviews", kwargs, self.review_result)


def test_query_service_forwards_owner_scope_history_and_limit() -> None:
    repository = FakeRepository()
    service = TypedMemoryQueryService(repository)
    assert service.preferences(
        owner_id="query-owner",
        include_history=True,
        limit=25,
    ).records == (preference(),)
    assert service.profile(
        owner_id="query-owner",
        relationship_id=RELATIONSHIP_ID,
        include_history=False,
        limit=10,
    ).records == (profile(),)
    assert repository.calls[0] == (
        "preferences",
        {"owner_id": "query-owner", "include_history": True, "limit": 25},
    )


def test_missing_or_observed_profile_scope_maps_to_safe_not_found() -> None:
    repository = FakeRepository()
    repository.profile_result = None
    with pytest.raises(TypedMemoryQueryServiceError) as error:
        TypedMemoryQueryService(repository).profile(
            owner_id="query-owner",
            relationship_id=RELATIONSHIP_ID,
            include_history=False,
            limit=50,
        )
    assert error.value.code == "memory_scope_not_found"


def test_repository_failure_and_invalid_projection_are_hidden() -> None:
    repository = FakeRepository()
    repository.failure = RuntimeError("database password leaked")
    with pytest.raises(TypedMemoryQueryServiceError) as error:
        TypedMemoryQueryService(repository).preferences(
            owner_id="query-owner",
            include_history=False,
            limit=50,
        )
    assert error.value.code == "service_unavailable"
    assert "password" not in str(error.value)

    repository.failure = None
    repository.preference_result = [preference()]
    with pytest.raises(TypedMemoryQueryServiceError) as invalid:
        TypedMemoryQueryService(repository).preferences(
            owner_id="query-owner",
            include_history=False,
            limit=50,
        )
    assert invalid.value.code == "service_unavailable"


def test_typed_memory_page_rejects_more_than_public_query_limit() -> None:
    with pytest.raises(ValueError):
        TypedMemoryPage(records=(preference(),) * 101)
