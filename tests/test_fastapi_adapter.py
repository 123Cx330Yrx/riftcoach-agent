from __future__ import annotations

import ast
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.actor import StaticActorContextProvider
from app.api.main import create_app
from app.api.task_models import ReadinessResult
from tests.player_link_api_stubs import UnusedPlayerLinkService
from app.product.run_query import RunView
from app.runtime.models import RuntimeStatus
from app.tasks.models import (
    CreateReviewTaskCommand,
    ReviewTaskView,
    TaskCreateDisposition,
    TaskCreateResult,
    TaskStatus,
)


NOW = datetime(2026, 8, 18, 9, 0, 0, tzinfo=timezone.utc)
TASK_ID = UUID("30000000-0000-4000-8000-000000000001")
RUN_ID = "review_fastapi_adapter_1"


def queued_task() -> ReviewTaskView:
    return ReviewTaskView(
        schema_version="1.0",
        task_id=TASK_ID,
        run_id=RUN_ID,
        status=TaskStatus.QUEUED,
        created_at=NOW,
        updated_at=NOW,
        claimed_at=None,
        finished_at=None,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
    )


class FakeTaskService:
    def __init__(self) -> None:
        self.commands: list[CreateReviewTaskCommand] = []

    def create(self, command: CreateReviewTaskCommand) -> TaskCreateResult:
        self.commands.append(command)
        return TaskCreateResult(
            disposition=TaskCreateDisposition.CREATED,
            task=queued_task(),
        )

    def get_task(self, *, owner_id: str, task_id: UUID) -> ReviewTaskView:
        del owner_id, task_id
        return queued_task()

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> ReviewTaskView:
        del owner_id, run_id
        return queued_task()


class ForbiddenRunQuery:
    def get_run(self, run_id: str) -> RunView:
        del run_id
        raise AssertionError("queued task must not read file run data")

    def get_report(self, run_id: str) -> str:
        del run_id
        raise AssertionError("queued task must not read report body")


class ReadyProbe:
    def check(self) -> ReadinessResult:
        return ReadinessResult.ready()


def app_and_service() -> tuple[TestClient, FakeTaskService]:
    service = FakeTaskService()
    app = create_app(
        task_service=service,
        player_link_service=UnusedPlayerLinkService(),
        query_service=ForbiddenRunQuery(),
        actor_provider=StaticActorContextProvider(
            owner_id="adapter-owner",
            profile="test",
        ),
        readiness_probe=ReadyProbe(),
    )
    return TestClient(app), service


def test_adapter_does_not_import_cli_or_agent_orchestrators() -> None:
    tree = ast.parse(Path("app/api/main.py").read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    forbidden_prefixes = (
        "scripts",
        "app.harness",
        "app.providers",
        "app.runtime.runtime",
        "app.skills.router",
        "app.lol",
        "app.workers",
    )
    assert not any(
        module.startswith(forbidden_prefixes)
        for module in imported_modules
    )


def test_app_factory_and_openapi_do_not_read_keys_or_open_io(monkeypatch) -> None:
    original_getenv = os.getenv

    def guarded_getenv(key, default=None):
        if key in {
            "RIOT_API_KEY",
            "ZHIPU_API_KEY",
            "DEEPSEEK_API_KEY",
            "DATABASE_URL",
        }:
            raise AssertionError("explicit app factory must not read secrets")
        return original_getenv(key, default)

    def forbidden_io(*args, **kwargs):
        del args, kwargs
        raise AssertionError("explicit app factory must not perform I/O")

    monkeypatch.setattr("os.getenv", guarded_getenv)
    monkeypatch.setattr("psycopg.connect", forbidden_io)
    monkeypatch.setattr("requests.sessions.Session.request", forbidden_io)

    http, _service = app_and_service()
    document = http.get("/openapi.json").json()

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


def test_post_is_only_an_enqueue_adapter_and_never_returns_report_body() -> None:
    http, service = app_and_service()

    response = http.post(
        "/reviews/recent",
        headers={"Idempotency-Key": "adapter-request-1"},
        json={"riot_id": "DemoPlayer#TEST", "focus": "survival"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert "output" not in response.json()
    assert "publication_status" not in response.json()
    assert set(response.json()) == {
        "schema_version",
        "disposition",
        "task_id",
        "run_id",
        "status",
        "links",
    }
    assert len(service.commands) == 1
    assert service.commands[0].owner_id == "adapter-owner"


def test_queued_run_and_report_are_not_read_from_artifact_store() -> None:
    http, _service = app_and_service()

    run = http.get(f"/runs/{RUN_ID}")
    report = http.get(f"/runs/{RUN_ID}/report")

    assert run.status_code == report.status_code == 409
    assert run.json()["code"] == report.json()["code"] == "run_not_ready"


def test_old_sync_health_path_and_deferred_product_paths_do_not_exist() -> None:
    http, _service = app_and_service()

    assert http.get("/health").status_code == 404
    assert http.get(f"/runs/{RUN_ID}/status").status_code == 404
    assert http.post(f"/runs/{RUN_ID}/follow-ups", json={}).status_code == 404
    assert http.get(f"/runs/{RUN_ID}/events").status_code == 404


def test_liveness_and_readiness_are_separate_contracts() -> None:
    http, _service = app_and_service()

    assert http.get("/health/live").json()["status"] == "ok"
    assert http.get("/health/ready").json()["status"] == "ready"
