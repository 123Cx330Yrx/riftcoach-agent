from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.auth.session import (
    AuthSessionBoundary,
    CookiePolicy,
    InMemoryAuthSessionStore,
)
from app.product.run_query import RunView
from app.tasks.models import ReviewTaskView, TaskStatus
from tests.player_link_api_stubs import UnusedPlayerLinkService


TASK_ID = UUID("93000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 24, 5, 0, tzinfo=timezone.utc)


class RecordingTaskService:
    def __init__(self) -> None:
        self.owners: list[str] = []

    def create(self, command):
        del command
        raise AssertionError("auth tests do not create review tasks")

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView:
        self.owners.append(owner_id)
        assert task_id == TASK_ID
        return ReviewTaskView(
            schema_version="1.0",
            task_id=TASK_ID,
            run_id="review_auth_boundary_1",
            status=TaskStatus.QUEUED,
            created_at=NOW,
            updated_at=NOW,
            claimed_at=None,
            finished_at=None,
            terminal_reason=None,
            publication_status=None,
            report_available=False,
        )

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        del run_id
        return self.get_task(owner_id=owner_id, task_id=TASK_ID)


class ForbiddenRunQuery:
    def get_run(self, run_id: str) -> RunView:
        del run_id
        raise AssertionError("auth tests do not read run data")

    def get_report(self, run_id: str) -> str:
        del run_id
        raise AssertionError("auth tests do not read report data")


class ReadyProbe:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


def build_client(
    *,
    service: AuthSessionBoundary | None,
    store: InMemoryAuthSessionStore | None = None,
) -> tuple[TestClient, RecordingTaskService, InMemoryAuthSessionStore]:
    selected_store = store or InMemoryAuthSessionStore()
    task_service = RecordingTaskService()
    app = create_app(
        task_service=task_service,
        player_link_service=UnusedPlayerLinkService(),
        query_service=ForbiddenRunQuery(),
        actor_provider=StaticActorContextProvider(
            owner_id="static-owner-must-not-win",
            profile="test",
        ),
        readiness_probe=ReadyProbe(),
        auth_session_service=service,
        auth_cookie_policy=CookiePolicy(secure=True),
    )
    return TestClient(app, base_url="https://testserver"), task_service, selected_store


def test_unconfigured_session_endpoint_fails_closed() -> None:
    client, _tasks, _store = build_client(service=None)

    response = client.post("/auth/session")

    assert response.status_code == 503
    assert response.json() == {"code": "auth_unavailable"}


def test_session_issue_uses_secure_opaque_cookie_and_server_owner() -> None:
    store = InMemoryAuthSessionStore()
    boundary = AuthSessionBoundary(
        store=store,
        owner_provider=lambda: "owner-a",
        ttl=timedelta(minutes=30),
    )
    client, tasks, _store = build_client(service=boundary, store=store)

    issued = client.post("/auth/session", json={"owner_id": "attacker-owner"})

    assert issued.status_code == 200
    assert set(issued.json()) == {"schema_version", "csrf_token", "expires_at"}
    set_cookie = issued.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "secure" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "attacker-owner" not in set_cookie

    task = client.get(f"/tasks/{TASK_ID}")
    assert task.status_code == 200
    assert tasks.owners == ["owner-a"]


def test_session_enabled_routes_reject_missing_expired_and_revoked_cookies() -> None:
    store = InMemoryAuthSessionStore()
    boundary = AuthSessionBoundary(store=store, owner_provider=lambda: "owner-a")
    client, _tasks, _store = build_client(service=boundary, store=store)

    assert client.get(f"/tasks/{TASK_ID}").json() == {
        "code": "authentication_required"
    }

    expired = store.issue(
        owner_id="owner-a",
        now=datetime.now(timezone.utc) - timedelta(minutes=5),
        ttl=timedelta(minutes=1),
    )
    client.cookies.set("riftcoach_session", expired.cookie_value)
    expired_response = client.get(f"/tasks/{TASK_ID}")
    assert expired_response.status_code == 401
    assert expired_response.json() == {"code": "auth_session_expired"}

    client.cookies.clear()
    issued = client.post("/auth/session")
    csrf_token = issued.json()["csrf_token"]
    assert client.delete(
        "/auth/session",
        headers={"X-CSRF-Token": "wrong-token"},
    ).json() == {"code": "csrf_invalid"}

    revoked = client.delete(
        "/auth/session",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert revoked.status_code == 204
    assert "riftcoach_session=" in revoked.headers["set-cookie"].lower()
    assert client.get(f"/tasks/{TASK_ID}").json() == {
        "code": "authentication_required"
    }


def test_mutating_routes_require_csrf_only_when_session_auth_is_enabled() -> None:
    store = InMemoryAuthSessionStore()
    boundary = AuthSessionBoundary(store=store, owner_provider=lambda: "owner-a")
    client, _tasks, _store = build_client(service=boundary, store=store)
    issued = client.post("/auth/session")

    missing = client.post("/reviews/recent", json={})
    wrong = client.post(
        "/reviews/recent",
        json={},
        headers={"X-CSRF-Token": "wrong"},
    )
    passed_boundary = client.post(
        "/reviews/recent",
        json={},
        headers={"X-CSRF-Token": issued.json()["csrf_token"]},
    )

    assert missing.status_code == 403
    assert missing.json() == {"code": "csrf_invalid"}
    assert wrong.status_code == 403
    assert wrong.json() == {"code": "csrf_invalid"}
    assert passed_boundary.status_code == 422
    assert passed_boundary.json() == {"code": "request_invalid"}
