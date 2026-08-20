from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.memory.models import RelationshipRole
from app.memory.typed_models import (
    MemoryTargetKind,
    MemoryTargetStatus,
    TypedMemoryPage,
    TypedMemoryRecordView,
)
from app.memory.typed_service import TypedMemoryQueryServiceError


OWNER = "typed-api-owner"
RELATIONSHIP_ID = UUID("94000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 20, 18, 0, tzinfo=timezone.utc)


class UnusedTaskService:
    def create(self, command):
        raise AssertionError

    def get_task(self, **kwargs):
        raise AssertionError

    def get_task_by_run_id(self, **kwargs):
        raise AssertionError


class UnusedPlayerLinkService:
    def create(self, command):
        raise AssertionError

    def get_link(self, **kwargs):
        raise AssertionError


class UnusedRunQuery:
    def get_run(self, run_id):
        raise AssertionError

    def get_report(self, run_id):
        raise AssertionError


class ReadyProbe:
    def check(self):
        return ReadinessResult.ready()


def record(kind: MemoryTargetKind) -> TypedMemoryRecordView:
    player_scoped = kind is not MemoryTargetKind.OWNER_PREFERENCE
    return TypedMemoryRecordView(
        record_id=UUID("94000000-0000-4000-8000-000000000002"),
        target_kind=kind,
        relationship_id=RELATIONSHIP_ID if player_scoped else None,
        relationship_role=RelationshipRole.SELF if player_scoped else None,
        memory_key="main_role" if player_scoped else "report_language",
        version=1,
        status=MemoryTargetStatus.ACTIVE,
        payload={"value": "TOP" if player_scoped else "zh-CN"},
        created_at=NOW,
        updated_at=NOW,
    )


class FakeTypedQueryService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.error: Exception | None = None

    def _result(self, operation, kwargs, page):
        self.calls.append((operation, kwargs))
        if self.error is not None:
            raise self.error
        return page

    def preferences(self, **kwargs):
        return self._result(
            "preferences",
            kwargs,
            TypedMemoryPage(records=(record(MemoryTargetKind.OWNER_PREFERENCE),)),
        )

    def profile(self, **kwargs):
        return self._result(
            "profile",
            kwargs,
            TypedMemoryPage(records=(record(MemoryTargetKind.PLAYER_PROFILE),)),
        )

    def reviews(self, **kwargs):
        return self._result("reviews", kwargs, TypedMemoryPage(records=()))


def client(service: FakeTypedQueryService | None = None, *, inject: bool = True) -> TestClient:
    kwargs = {}
    if inject:
        kwargs["typed_memory_query_service"] = service or FakeTypedQueryService()
    return TestClient(
        create_app(
            task_service=UnusedTaskService(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=UnusedRunQuery(),
            actor_provider=StaticActorContextProvider(owner_id=OWNER, profile="test"),
            readiness_probe=ReadyProbe(),
            **kwargs,
        )
    )


def test_preference_and_player_queries_use_trusted_owner_and_bounded_controls() -> None:
    service = FakeTypedQueryService()
    http = client(service)
    preference_response = http.get("/memory/preferences?include_history=true&limit=25")
    profile_response = http.get(
        f"/memory/players/{RELATIONSHIP_ID}/profile?include_history=false&limit=10"
    )
    assert preference_response.status_code == 200
    assert preference_response.json()["records"][0]["payload"] == {"value": "zh-CN"}
    assert profile_response.status_code == 200
    assert service.calls == [
        (
            "preferences",
            {"owner_id": OWNER, "include_history": True, "limit": 25},
        ),
        (
            "profile",
            {
                "owner_id": OWNER,
                "relationship_id": RELATIONSHIP_ID,
                "include_history": False,
                "limit": 10,
            },
        ),
    ]
    body = profile_response.json()["records"][0]
    for private_key in ("player_subject_id", "puuid", "source_candidate_id"):
        assert private_key not in body


def test_scope_not_found_and_missing_service_fail_closed() -> None:
    service = FakeTypedQueryService()
    service.error = TypedMemoryQueryServiceError("memory_scope_not_found")
    missing_scope = client(service).get(f"/memory/players/{RELATIONSHIP_ID}/profile")
    assert missing_scope.status_code == 404
    assert missing_scope.json() == {"code": "memory_scope_not_found"}

    unavailable = client(inject=False).get("/memory/preferences")
    assert unavailable.status_code == 503
    assert unavailable.json() == {"code": "service_unavailable"}


def test_query_validation_and_openapi_are_bounded() -> None:
    http = client()
    assert http.get("/memory/preferences?limit=0").status_code == 422
    assert http.get("/memory/preferences?limit=101").status_code == 422
    document = http.get("/openapi.json").json()
    assert "/memory/preferences" in document["paths"]
    assert "/memory/players/{relationship_id}/profile" in document["paths"]
    assert "/memory/players/{relationship_id}/reviews" in document["paths"]
