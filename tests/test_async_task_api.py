from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.actor import (
    StaticActorContextProvider,
    UnavailableActorContextProvider,
)
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from app.product.recent_review import RecentReviewProductRequest
from app.product.run_query import RunQueryError, RunView
from app.runtime.models import RuntimeStatus
from app.runtime.signals import RuntimePublicationStatus
from app.tasks.models import (
    CreateReviewTaskCommand,
    ReviewTaskView,
    TaskCreateDisposition,
    TaskCreateResult,
    TaskPublicationStatus,
    TaskStatus,
)
from app.tasks.service import TaskServiceError
from tests.player_link_api_stubs import UnusedPlayerLinkService


NOW = datetime(2026, 8, 18, 8, 0, 0, tzinfo=timezone.utc)
TASK_ID = UUID("20000000-0000-4000-8000-000000000001")
RUN_ID = "review_async_api_1"


def task_view(
    *,
    status: TaskStatus = TaskStatus.QUEUED,
    report_available: bool = False,
) -> ReviewTaskView:
    claimed_at = NOW + timedelta(seconds=1) if status is not TaskStatus.QUEUED else None
    finished_at = (
        NOW + timedelta(seconds=2)
        if status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED}
        else None
    )
    return ReviewTaskView(
        schema_version="1.0",
        task_id=TASK_ID,
        run_id=RUN_ID,
        status=status,
        created_at=NOW,
        updated_at=finished_at or claimed_at or NOW,
        claimed_at=claimed_at,
        finished_at=finished_at,
        terminal_reason=(
            "quality_gate_passed"
            if status is TaskStatus.SUCCEEDED
            else "review_runtime_failed"
            if status is TaskStatus.FAILED
            else None
        ),
        publication_status=(
            TaskPublicationStatus.PUBLISHED
            if status is TaskStatus.SUCCEEDED
            else None
        ),
        report_available=report_available,
    )


class FakeTaskService:
    def __init__(self) -> None:
        self.created = TaskCreateResult(
            disposition=TaskCreateDisposition.CREATED,
            task=task_view(),
        )
        self.lookup = task_view()
        self.error: Exception | None = None
        self.commands: list[CreateReviewTaskCommand] = []
        self.task_calls: list[tuple[str, UUID]] = []
        self.run_calls: list[tuple[str, str]] = []

    def create(self, command: CreateReviewTaskCommand) -> TaskCreateResult:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return self.created

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView:
        self.task_calls.append((owner_id, task_id))
        if self.error is not None:
            raise self.error
        return self.lookup

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        self.run_calls.append((owner_id, run_id))
        if self.error is not None:
            raise self.error
        return self.lookup


class FakeRunQuery:
    def __init__(self) -> None:
        self.run = RunView(
            run_id=RUN_ID,
            runtime_status=RuntimeStatus.COMPLETED,
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            report_available=True,
        )
        self.report = "# reviewed report\n"
        self.error: Exception | None = None
        self.calls: list[tuple[str, str]] = []

    def get_run(self, run_id: str) -> RunView:
        self.calls.append(("run", run_id))
        if self.error is not None:
            raise self.error
        return self.run

    def get_report(self, run_id: str) -> str:
        self.calls.append(("report", run_id))
        if self.error is not None:
            raise self.error
        return self.report


class FakeReadinessProbe:
    def __init__(self, result: ReadinessResult | None = None) -> None:
        self.result = result or ReadinessResult.ready()
        self.calls = 0

    def check(self) -> ReadinessResult:
        self.calls += 1
        return self.result


def client(
    *,
    task_service: FakeTaskService | None = None,
    query_service: FakeRunQuery | None = None,
    actor_provider: Any | None = None,
    readiness_probe: FakeReadinessProbe | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            task_service=task_service or FakeTaskService(),
            player_link_service=UnusedPlayerLinkService(),
            query_service=query_service or FakeRunQuery(),
            actor_provider=actor_provider
            or StaticActorContextProvider(owner_id="owner-1", profile="test"),
            readiness_probe=readiness_probe or FakeReadinessProbe(),
        )
    )


def post_recent(http: TestClient, **overrides: Any):
    payload = {"riot_id": "DemoPlayer#TEST", "focus": "survival"}
    payload.update(overrides)
    return http.post(
        "/reviews/recent",
        headers={"Idempotency-Key": "request-1"},
        json=payload,
    )


def test_openapi_versions_the_async_contract_and_exact_paths() -> None:
    document = client().get("/openapi.json").json()

    assert document["info"]["version"] == "2.0"
    assert set(document["paths"]) == {
        "/conversations",
        "/conversations/{conversation_id}",
        "/conversations/{conversation_id}/messages",
        "/conversations/{conversation_id}/archive",
        "/conversations/{conversation_id}/hide",
            "/conversations/{conversation_id}/reviews/recent",
            "/conversations/{conversation_id}/memory-candidates",
            "/memory-candidates/{candidate_id}",
            "/memory-candidates/{candidate_id}/accept",
            "/memory-candidates/{candidate_id}/reject",
        "/reviews/recent",
        "/player-links",
        "/player-links/{link_task_id}",
        "/tasks/{task_id}",
        "/runs/{run_id}",
        "/runs/{run_id}/report",
        "/health/live",
        "/health/ready",
    }
    assert document["paths"]["/reviews/recent"]["post"]["responses"].get("202")
    assert "201" not in document["paths"]["/reviews/recent"]["post"]["responses"]


def test_post_commits_task_and_returns_202_receipt_without_private_input() -> None:
    service = FakeTaskService()

    response = post_recent(client(task_service=service))

    assert response.status_code == 202
    assert response.json() == {
        "schema_version": "1.0",
        "disposition": "created",
        "task_id": str(TASK_ID),
        "run_id": RUN_ID,
        "status": "queued",
        "links": {
            "task": f"/tasks/{TASK_ID}",
            "run": f"/runs/{RUN_ID}",
            "report": f"/runs/{RUN_ID}/report",
        },
    }
    assert service.commands == [
        CreateReviewTaskCommand(
            owner_id="owner-1",
            idempotency_key="request-1",
            request=RecentReviewProductRequest(
                riot_id="DemoPlayer#TEST",
                focus="survival",
            ),
        )
    ]
    assert "DemoPlayer" not in response.text
    assert "owner-1" not in response.text


def test_post_replay_keeps_202_and_reports_replayed_disposition() -> None:
    service = FakeTaskService()
    service.created = service.created.model_copy(
        update={"disposition": TaskCreateDisposition.REPLAYED}
    )

    response = post_recent(client(task_service=service))

    assert response.status_code == 202
    assert response.json()["disposition"] == "replayed"
    assert response.json()["task_id"] == str(TASK_ID)


def test_post_requires_bounded_idempotency_key_before_service_call() -> None:
    service = FakeTaskService()
    http = client(task_service=service)

    missing = http.post(
        "/reviews/recent",
        json={"riot_id": "DemoPlayer#TEST"},
    )
    invalid = http.post(
        "/reviews/recent",
        headers={"Idempotency-Key": "contains spaces"},
        json={"riot_id": "DemoPlayer#TEST"},
    )

    assert missing.status_code == invalid.status_code == 422
    assert missing.json() == invalid.json() == {"code": "request_invalid"}
    assert service.commands == []


def test_owner_cannot_be_supplied_in_body_or_internal_headers() -> None:
    service = FakeTaskService()
    http = client(task_service=service)

    response = http.post(
        "/reviews/recent",
        headers={
            "Idempotency-Key": "request-1",
            "X-Owner-Id": "attacker-owner",
        },
        json={
            "riot_id": "DemoPlayer#TEST",
            "owner_id": "attacker-owner",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"code": "request_invalid"}
    assert service.commands == []


@pytest.mark.parametrize(
    ("service_code", "status", "public_code"),
    (
        ("idempotency_conflict", 409, "idempotency_conflict"),
        ("owner_capacity_exceeded", 503, "task_capacity_exceeded"),
        ("global_capacity_exceeded", 503, "task_capacity_exceeded"),
        ("task_persistence_failed", 503, "service_unavailable"),
        ("task_identity_invalid", 503, "service_unavailable"),
    ),
)
def test_post_maps_task_failures_to_safe_http_errors(
    service_code: str,
    status: int,
    public_code: str,
) -> None:
    service = FakeTaskService()
    service.error = TaskServiceError(service_code)  # type: ignore[arg-type]

    response = post_recent(client(task_service=service))

    assert response.status_code == status
    assert response.json() == {"code": public_code}


def test_unavailable_actor_fails_closed_without_creating_task() -> None:
    service = FakeTaskService()

    response = post_recent(
        client(
            task_service=service,
            actor_provider=UnavailableActorContextProvider(),
        )
    )

    assert response.status_code == 503
    assert response.json() == {"code": "service_unavailable"}
    assert service.commands == []


def test_task_query_is_owner_scoped_and_returns_safe_projection() -> None:
    service = FakeTaskService()

    response = client(task_service=service).get(f"/tasks/{TASK_ID}")

    assert response.status_code == 200
    assert response.json()["task_id"] == str(TASK_ID)
    assert response.json()["status"] == "queued"
    assert "owner_id" not in response.json()
    assert service.task_calls == [("owner-1", TASK_ID)]


def test_invalid_or_unowned_task_is_indistinguishable_not_found() -> None:
    service = FakeTaskService()
    service.error = TaskServiceError("task_not_found")
    http = client(task_service=service)

    invalid = http.get("/tasks/not-a-uuid")
    hidden = http.get(f"/tasks/{TASK_ID}")

    assert invalid.status_code == hidden.status_code == 404
    assert invalid.json() == hidden.json() == {"code": "task_not_found"}


@pytest.mark.parametrize("status", (TaskStatus.QUEUED, TaskStatus.RUNNING))
def test_nonterminal_run_is_409_without_touching_artifact_store(
    status: TaskStatus,
) -> None:
    service = FakeTaskService()
    service.lookup = task_view(status=status)
    query = FakeRunQuery()

    response = client(task_service=service, query_service=query).get(
        f"/runs/{RUN_ID}"
    )

    assert response.status_code == 409
    assert response.json() == {"code": "run_not_ready", "run_id": RUN_ID}
    assert query.calls == []
    assert service.run_calls == [("owner-1", RUN_ID)]


def test_succeeded_run_is_owner_checked_before_strict_artifact_query() -> None:
    service = FakeTaskService()
    service.lookup = task_view(status=TaskStatus.SUCCEEDED, report_available=True)
    query = FakeRunQuery()

    response = client(task_service=service, query_service=query).get(
        f"/runs/{RUN_ID}"
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == RUN_ID
    assert service.run_calls == [("owner-1", RUN_ID)]
    assert query.calls == [("run", RUN_ID)]


def test_succeeded_sql_task_with_missing_artifacts_is_integrity_failure() -> None:
    service = FakeTaskService()
    service.lookup = task_view(status=TaskStatus.SUCCEEDED, report_available=True)
    query = FakeRunQuery()
    query.error = RunQueryError("run_not_found")

    response = client(task_service=service, query_service=query).get(
        f"/runs/{RUN_ID}"
    )

    assert response.status_code == 500
    assert response.json() == {"code": "run_integrity_failed", "run_id": RUN_ID}


def test_report_not_available_is_409_without_reading_artifact_body() -> None:
    service = FakeTaskService()
    service.lookup = task_view(status=TaskStatus.SUCCEEDED, report_available=False)
    query = FakeRunQuery()

    response = client(task_service=service, query_service=query).get(
        f"/runs/{RUN_ID}/report"
    )

    assert response.status_code == 409
    assert response.json() == {"code": "report_not_available", "run_id": RUN_ID}
    assert query.calls == []


def test_available_report_is_owner_checked_and_returned_as_markdown() -> None:
    service = FakeTaskService()
    service.lookup = task_view(status=TaskStatus.SUCCEEDED, report_available=True)
    query = FakeRunQuery()

    response = client(task_service=service, query_service=query).get(
        f"/runs/{RUN_ID}/report"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert response.text == "# reviewed report\n"
    assert service.run_calls == [("owner-1", RUN_ID)]
    assert query.calls == [("report", RUN_ID)]


def test_lookup_persistence_failure_is_sanitized() -> None:
    service = FakeTaskService()
    service.error = RuntimeError(
        "postgresql://secret@private.example/riftcoach C:\\private\\.env"
    )

    response = client(task_service=service).get(f"/tasks/{TASK_ID}")

    assert response.status_code == 503
    assert response.json() == {"code": "service_unavailable"}
    assert "private.example" not in response.text
    assert "secret" not in response.text


def test_liveness_never_calls_readiness_dependencies() -> None:
    probe = FakeReadinessProbe()

    response = client(readiness_probe=probe).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "2.0",
        "schema_version": "1.0",
    }
    assert probe.calls == 0


@pytest.mark.parametrize(
    ("result", "status", "body"),
    (
        (
            ReadinessResult.ready(),
            200,
            {"status": "ready", "api_version": "2.0", "schema_version": "1.0"},
        ),
        (
            ReadinessResult.not_ready("database_unavailable"),
            503,
            {
                "status": "not_ready",
                "code": "database_unavailable",
                "api_version": "2.0",
                "schema_version": "1.0",
            },
        ),
        (
            ReadinessResult.not_ready("migration_not_current"),
            503,
            {
                "status": "not_ready",
                "code": "migration_not_current",
                "api_version": "2.0",
                "schema_version": "1.0",
            },
        ),
    ),
)
def test_readiness_projects_only_safe_bounded_state(
    result: ReadinessResult,
    status: int,
    body: dict[str, Any],
) -> None:
    response = client(readiness_probe=FakeReadinessProbe(result)).get(
        "/health/ready"
    )

    assert response.status_code == status
    assert response.json() == body
