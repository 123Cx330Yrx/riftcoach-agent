from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.product.run_query import RunView
from app.runtime.models import RuntimeStatus
from app.runtime.signals import RuntimePublicationStatus
from app.tasks.models import ReviewTaskView, TaskStatus
from app.tasks.reliable_runtime import (
    TaskCancelDisposition,
    TaskCancelResult,
    TaskEventPage,
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
)
from app.tasks.service import TaskServiceError
from tests.player_link_api_stubs import UnusedPlayerLinkService


NOW = datetime(2026, 8, 22, 18, 0, tzinfo=timezone.utc)
TASK_ID = UUID("85000000-0000-4000-8000-000000000001")
RUN_ID = "review_reliable_api_1"


def event() -> TaskLifecycleEvent:
    return TaskLifecycleEvent.create(
        event_cursor=7,
        task_sequence=1,
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id="owner-1",
        event_kind=TaskLifecycleEventKind.CREATED,
        status_after=TaskStatus.QUEUED,
        lease_generation=0,
        operation_identity="created",
        occurred_at=NOW,
    )


def task_view(status: TaskStatus) -> ReviewTaskView:
    active = status in {TaskStatus.RUNNING, TaskStatus.RECOVERY_REQUIRED}
    terminal = status in {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    }
    return ReviewTaskView(
        schema_version="1.0",
        task_id=TASK_ID,
        run_id=RUN_ID,
        status=status,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=2),
        claimed_at=NOW + timedelta(seconds=1) if active or terminal else None,
        finished_at=NOW + timedelta(seconds=2) if terminal else None,
        terminal_reason=(
            "user_requested"
            if status is TaskStatus.CANCELLED
            else "worker_execution_failed"
            if status is TaskStatus.FAILED
            else None
        ),
        publication_status=None,
        report_available=False,
    )


class TaskService:
    def __init__(self) -> None:
        self.cancel = TaskCancelResult(
            task_id=TASK_ID,
            disposition=TaskCancelDisposition.REQUESTED,
            status=TaskStatus.RUNNING,
        )
        self.page = TaskEventPage(
            after_cursor=0,
            next_cursor=7,
            limit=50,
            has_more=False,
            events=(event(),),
        )
        self.lookup = task_view(TaskStatus.RUNNING)
        self.error: Exception | None = None
        self.cancel_calls = []
        self.event_calls = []

    def create(self, _command):
        raise AssertionError("test does not create tasks")

    def get_task(self, *, owner_id, task_id):
        del owner_id, task_id
        if self.error is not None:
            raise self.error
        return self.lookup

    def get_task_by_run_id(self, *, owner_id, run_id):
        del owner_id, run_id
        if self.error is not None:
            raise self.error
        return self.lookup

    def request_cancel(self, *, owner_id, task_id, request_id):
        self.cancel_calls.append((owner_id, task_id, request_id))
        if self.error is not None:
            raise self.error
        return self.cancel

    def read_events(self, *, owner_id, task_id, after_cursor, limit):
        self.event_calls.append((owner_id, task_id, after_cursor, limit))
        if self.error is not None:
            raise self.error
        return self.page.model_copy(
            update={"after_cursor": after_cursor, "limit": limit}
        )


class Query:
    def __init__(self) -> None:
        self.calls = []

    def get_run(self, run_id):
        self.calls.append(("run", run_id))
        return RunView(
            run_id=run_id,
            runtime_status=RuntimeStatus.COMPLETED,
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            report_available=True,
        )

    def get_report(self, run_id):
        self.calls.append(("report", run_id))
        return "# private report"


class Readiness:
    def check(self):
        return ReadinessResult.ready()


def client(service: TaskService, *, query: Query | None = None) -> TestClient:
    return TestClient(
        create_app(
            task_service=service,
            player_link_service=UnusedPlayerLinkService(),
            query_service=query or Query(),
            actor_provider=StaticActorContextProvider(
                owner_id="owner-1",
                profile="test",
            ),
            readiness_probe=Readiness(),
        )
    )


def test_cancel_requires_idempotency_and_projects_body_free_disposition() -> None:
    service = TaskService()

    response = client(service).post(
        f"/tasks/{TASK_ID}/cancel",
        headers={"Idempotency-Key": "cancel-request-1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "1.0",
        "task_id": str(TASK_ID),
        "disposition": "requested",
        "status": "running",
    }
    assert service.cancel_calls == [
        ("owner-1", TASK_ID, "cancel-request-1")
    ]
    assert "token" not in response.text.lower()
    assert client(service).post(f"/tasks/{TASK_ID}/cancel").status_code == 422


def test_cancel_and_event_owner_miss_are_safe_404() -> None:
    service = TaskService()
    service.error = TaskServiceError("task_not_found")
    http = client(service)

    cancelled = http.post(
        f"/tasks/{TASK_ID}/cancel",
        headers={"Idempotency-Key": "cancel-request-1"},
    )
    events = http.get(f"/tasks/{TASK_ID}/events")

    assert cancelled.status_code == events.status_code == 404
    assert cancelled.json() == events.json() == {"code": "task_not_found"}


def test_event_page_is_cursor_bounded_and_hides_internal_fields() -> None:
    service = TaskService()

    response = client(service).get(
        f"/tasks/{TASK_ID}/events?after_cursor=0&limit=50"
    )

    assert response.status_code == 200
    assert service.event_calls == [("owner-1", TASK_ID, 0, 50)]
    payload = response.json()
    assert payload["next_cursor"] == 7
    assert payload["events"][0]["event_kind"] == "created"
    serialized = response.text.lower()
    for forbidden in (
        "owner_id",
        "worker_id",
        "checkpoint_reference",
        "lease_token",
        "operation_identity",
        "request_payload",
        "puuid",
    ):
        assert forbidden not in serialized
    assert client(service).get(
        f"/tasks/{TASK_ID}/events?after_cursor=-1"
    ).status_code == 422
    assert client(service).get(
        f"/tasks/{TASK_ID}/events?limit=101"
    ).status_code == 422


def test_persistence_failures_are_sanitized_for_cancel_and_events() -> None:
    service = TaskService()
    service.error = RuntimeError("postgresql://secret@private C:\\private\\.env")
    http = client(service)

    cancelled = http.post(
        f"/tasks/{TASK_ID}/cancel",
        headers={"Idempotency-Key": "cancel-request-1"},
    )
    events = http.get(f"/tasks/{TASK_ID}/events")

    assert cancelled.status_code == events.status_code == 503
    assert cancelled.json() == events.json() == {"code": "service_unavailable"}
    assert "secret" not in cancelled.text + events.text


def test_cancelled_and_recovery_required_never_query_run_artifacts() -> None:
    service = TaskService()
    query = Query()
    http = client(service, query=query)

    service.lookup = task_view(TaskStatus.RECOVERY_REQUIRED)
    recovering_run = http.get(f"/runs/{RUN_ID}")
    recovering_report = http.get(f"/runs/{RUN_ID}/report")
    service.lookup = task_view(TaskStatus.CANCELLED)
    cancelled_run = http.get(f"/runs/{RUN_ID}")
    cancelled_report = http.get(f"/runs/{RUN_ID}/report")

    assert recovering_run.status_code == recovering_report.status_code == 409
    assert recovering_run.json()["code"] == "run_not_ready"
    assert recovering_report.json()["code"] == "run_not_ready"
    assert cancelled_run.status_code == cancelled_report.status_code == 409
    assert cancelled_run.json()["code"] == "run_not_available"
    assert cancelled_report.json()["code"] == "report_not_available"
    assert query.calls == []
