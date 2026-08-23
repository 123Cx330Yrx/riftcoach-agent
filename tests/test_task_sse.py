from __future__ import annotations

import json
from datetime import timedelta

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.tasks.models import TaskStatus
from app.tasks.reliable_runtime import (
    TaskEventPage,
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
)
from app.tasks.service import TaskServiceError
from app.tasks.sse import (
    TaskEventStreamService,
    encode_task_event_frame,
    resolve_event_cursor,
)
from tests.player_link_api_stubs import UnusedPlayerLinkService
from tests.test_evidence_product_service import NOW, RUN_ID, TASK_ID, task


def created_event() -> TaskLifecycleEvent:
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


def terminal_event() -> TaskLifecycleEvent:
    return TaskLifecycleEvent.create(
        event_cursor=8,
        task_sequence=2,
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id="owner-1",
        event_kind=TaskLifecycleEventKind.SUCCEEDED,
        status_after=TaskStatus.SUCCEEDED,
        lease_generation=1,
        worker_id="worker-private",
        operation_identity="operation-private",
        reason="quality_gate_passed",
        occurred_at=NOW + timedelta(seconds=1),
    )


class Tasks:
    def __init__(self) -> None:
        self.error: Exception | None = None
        self.event_calls: list[tuple[str, object, int, int]] = []
        self.events = (created_event(), terminal_event())

    def create(self, _command):
        raise AssertionError("test does not create tasks")

    def get_task(self, *, owner_id, task_id):
        if self.error is not None:
            raise self.error
        assert owner_id == "owner-1" and task_id == TASK_ID
        return task()

    def get_task_by_run_id(self, **_kwargs):
        return task()

    def read_events(self, *, owner_id, task_id, after_cursor, limit):
        self.event_calls.append((owner_id, task_id, after_cursor, limit))
        if self.error is not None:
            raise self.error
        rows = tuple(event for event in self.events if event.event_cursor > after_cursor)
        rows = rows[:limit]
        return TaskEventPage(
            after_cursor=after_cursor,
            next_cursor=after_cursor if not rows else rows[-1].event_cursor,
            limit=limit,
            has_more=False,
            events=rows,
        )


class Query:
    def get_run(self, _run_id):
        raise AssertionError("SSE does not query artifacts")

    def get_report(self, _run_id):
        raise AssertionError("SSE does not query report bodies")


class Readiness:
    def check(self):
        return ReadinessResult.ready()


def stream_service(tasks: Tasks, *, max_polls: int = 2) -> TaskEventStreamService:
    return TaskEventStreamService(
        task_service=tasks,
        max_polls=max_polls,
        poll_interval_seconds=0,
        sleep=lambda _seconds: None,
    )


def client(tasks: Tasks) -> TestClient:
    return TestClient(
        create_app(
            task_service=tasks,
            player_link_service=UnusedPlayerLinkService(),
            query_service=Query(),
            actor_provider=StaticActorContextProvider(
                owner_id="owner-1",
                profile="test",
            ),
            readiness_probe=Readiness(),
            task_event_stream_service=stream_service(tasks),
        )
    )


def test_encoder_and_cursor_resolution_are_exact_and_body_free() -> None:
    frame = encode_task_event_frame(terminal_event())
    data = json.loads(frame.split("data: ", 1)[1])

    assert resolve_event_cursor(after_cursor=None, last_event_id=None) == 0
    assert resolve_event_cursor(after_cursor=7, last_event_id=None) == 7
    assert resolve_event_cursor(after_cursor=None, last_event_id="7") == 7
    assert resolve_event_cursor(after_cursor=7, last_event_id="7") == 7
    assert frame.startswith("id: 8\nevent: task.lifecycle\ndata: ")
    assert data["event_kind"] == "succeeded"
    for forbidden in (
        "owner_id",
        "worker_id",
        "operation_identity",
        "checkpoint_reference",
        "token",
    ):
        assert forbidden not in frame


def test_reconnect_replays_only_after_cursor_and_terminal_closes() -> None:
    tasks = Tasks()
    service = stream_service(tasks)

    initial = "".join(
        service.stream(owner_id="owner-1", task_id=TASK_ID, after_cursor=0)
    )
    reconnect = "".join(
        service.stream(owner_id="owner-1", task_id=TASK_ID, after_cursor=7)
    )

    assert initial.count("event: task.lifecycle") == 2
    assert reconnect.count("event: task.lifecycle") == 1
    assert "id: 7" not in reconnect
    assert "id: 8" in reconnect
    assert tasks.event_calls == [
        ("owner-1", TASK_ID, 0, 100),
        ("owner-1", TASK_ID, 7, 100),
    ]


def test_idle_keepalive_and_stream_failure_are_finite_and_sanitized() -> None:
    tasks = Tasks()
    tasks.events = ()
    idle = "".join(
        stream_service(tasks).stream(
            owner_id="owner-1", task_id=TASK_ID, after_cursor=0
        )
    )
    tasks.error = RuntimeError("postgresql://secret@private C:\\private\\trace")
    failed = "".join(
        stream_service(tasks).stream(
            owner_id="owner-1", task_id=TASK_ID, after_cursor=0
        )
    )

    assert idle == ": keep-alive\n\n: keep-alive\n\n"
    assert failed == 'event: stream.error\ndata: {"code":"service_unavailable"}\n\n'
    assert "secret" not in failed


def test_sse_api_supports_last_event_id_headers_conflict_and_owner_preflight() -> None:
    tasks = Tasks()
    http = client(tasks)

    response = http.get(
        f"/tasks/{TASK_ID}/events/stream",
        headers={"Last-Event-ID": "7"},
    )
    conflict = http.get(
        f"/tasks/{TASK_ID}/events/stream?after_cursor=6",
        headers={"Last-Event-ID": "7"},
    )
    invalid = http.get(
        f"/tasks/{TASK_ID}/events/stream",
        headers={"Last-Event-ID": "private-token"},
    )
    tasks.error = TaskServiceError("task_not_found")
    hidden = http.get(f"/tasks/{TASK_ID}/events/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert "id: 8" in response.text and "id: 7" not in response.text
    assert conflict.status_code == invalid.status_code == 422
    assert conflict.json() == invalid.json() == {"code": "request_invalid"}
    assert hidden.status_code == 404
    assert hidden.json() == {"code": "task_not_found"}
