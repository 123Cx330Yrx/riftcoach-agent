from __future__ import annotations

import importlib
import os
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.composition import (
    PostgresReadinessProbe,
    create_composed_app,
)
from app.api.actor import StaticActorContextProvider


VALID_ENV = {
    "DATABASE_URL": (
        "postgresql+psycopg://riftcoach:local-secret@localhost:5432/riftcoach"
    ),
    "RIFTCOACH_API_PROFILE": "test",
    "RIFTCOACH_LOCAL_OWNER_ID": "test-owner",
    "RIFTCOACH_RUNS_ROOT": "data/runs",
}


class ScalarResult:
    def scalar_one(self) -> int:
        return 1


class FakeConnection:
    def execute(self, statement: Any) -> ScalarResult:
        assert "SELECT 1" in str(statement)
        return ScalarResult()


class FakeEngine:
    def __init__(self, *, connect_error: Exception | None = None) -> None:
        self.connect_error = connect_error
        self.dispose_calls = 0

    @contextmanager
    def connect(self):
        if self.connect_error is not None:
            raise self.connect_error
        yield FakeConnection()

    def dispose(self) -> None:
        self.dispose_calls += 1


def test_composition_import_factory_and_openapi_are_key_and_io_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_getenv = os.getenv

    def guarded_getenv(key: str, default: str | None = None):
        if key in {
            "RIOT_API_KEY",
            "ZHIPU_API_KEY",
            "DEEPSEEK_API_KEY",
            "DATABASE_URL",
        }:
            raise AssertionError("import/OpenAPI must not read deployment secrets")
        return original_getenv(key, default)

    def forbidden_connect(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("import/OpenAPI must not connect to PostgreSQL or HTTP")

    monkeypatch.setattr("os.getenv", guarded_getenv)
    monkeypatch.setattr("psycopg.connect", forbidden_connect)
    monkeypatch.setattr("requests.sessions.Session.request", forbidden_connect)

    module = importlib.import_module("app.api.composition")
    app = module.create_composed_app(environment=VALID_ENV)

    assert app.version == "2.0"
    assert "/conversations" in app.openapi()["paths"]
    assert "/reviews/recent" in app.openapi()["paths"]


def test_clean_process_composition_import_and_openapi_are_io_free() -> None:
    project_root = Path(__file__).resolve().parents[1]
    probe = textwrap.dedent(
        """
        import os

        original_getenv = os.getenv

        def guarded_getenv(key, default=None):
            if key in {
                "RIOT_API_KEY",
                "ZHIPU_API_KEY",
                "DEEPSEEK_API_KEY",
                "DATABASE_URL",
            }:
                raise AssertionError("clean import read a deployment secret")
            return original_getenv(key, default)

        def forbidden_io(*_args, **_kwargs):
            raise AssertionError("clean import attempted external I/O")

        os.getenv = guarded_getenv

        import psycopg
        import requests.sessions
        import sqlalchemy

        psycopg.connect = forbidden_io
        requests.sessions.Session.request = forbidden_io
        sqlalchemy.create_engine = forbidden_io

        from app.api.composition import create_composed_app

        app = create_composed_app(
            environment={
                "DATABASE_URL": (
                    "postgresql+psycopg://riftcoach:local-secret@localhost:5432/"
                    "riftcoach"
                ),
                "RIFTCOACH_API_PROFILE": "test",
                "RIFTCOACH_LOCAL_OWNER_ID": "test-owner",
                "RIFTCOACH_RUNS_ROOT": "data/runs",
            }
        )
        paths = app.openapi()["paths"]
        assert "/conversations" in paths
        assert "/reviews/recent" in paths
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_lifespan_builds_process_resources_once_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = FakeEngine()
    calls: list[str] = []
    environment = {**VALID_ENV, "RIFTCOACH_RUNS_ROOT": str(tmp_path)}

    def fake_build_engine(settings: Any) -> FakeEngine:
        calls.append("engine")
        return engine

    def fake_session_factory(received: FakeEngine):
        assert received is engine
        calls.append("session_factory")
        return lambda: None

    monkeypatch.setattr("app.api.composition.build_engine", fake_build_engine)
    monkeypatch.setattr(
        "app.api.composition.build_session_factory",
        fake_session_factory,
    )

    app = create_composed_app(environment=environment)
    assert calls == []
    assert engine.dispose_calls == 0

    with TestClient(app) as http:
        assert http.get("/health/live").status_code == 200
        assert calls == ["engine", "session_factory"]
        assert app.state.database_engine is engine
        assert engine.dispose_calls == 0

    assert engine.dispose_calls == 1
    assert app.state.database_engine is None


def test_conversation_composition_failure_is_fail_closed_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = FakeEngine()
    environment = {**VALID_ENV, "RIFTCOACH_RUNS_ROOT": str(tmp_path)}
    monkeypatch.setattr(
        "app.api.composition.build_engine",
        lambda _settings: engine,
    )
    monkeypatch.setattr(
        "app.api.composition.build_session_factory",
        lambda _engine: (lambda: None),
    )
    monkeypatch.setattr(
        "app.api.composition.PostgresConversationRepository",
        lambda _factory: (_ for _ in ()).throw(
            RuntimeError("postgresql://secret@private.example/riftcoach")
        ),
    )

    app = create_composed_app(environment=environment)
    with TestClient(app) as http:
        live = http.get("/health/live")
        ready = http.get("/health/ready")
        conversation = http.post(
            "/conversations",
            headers={"Idempotency-Key": "request-1"},
            json={
                "relationship_id": "50000000-0000-4000-8000-000000000020"
            },
        )

    assert live.status_code == 200
    assert ready.status_code == 503
    assert ready.json() == {
        "schema_version": "1.0",
        "api_version": "2.0",
        "status": "not_ready",
        "code": "service_configuration_invalid",
    }
    assert conversation.status_code == 503
    assert conversation.json() == {"code": "service_unavailable"}
    assert "secret" not in conversation.text
    assert "private.example" not in conversation.text
    assert engine.dispose_calls == 1
    assert app.state.database_engine is None


@pytest.mark.parametrize(
    ("current", "head", "ready", "code"),
    (
        ("0001_review_tasks", "0001_review_tasks", True, None),
        ("0001_review_tasks", "0002_future", False, "migration_not_current"),
        (None, "0001_review_tasks", False, "migration_not_current"),
    ),
)
def test_postgres_readiness_requires_connectivity_and_exact_migration_head(
    current: str | None,
    head: str,
    ready: bool,
    code: str | None,
) -> None:
    probe = PostgresReadinessProbe(
        FakeEngine(),
        revision_reader=lambda _connection: (current, head),
    )

    result = probe.check()

    assert result.is_ready is ready
    assert result.code == code


def test_postgres_readiness_sanitizes_database_failure() -> None:
    probe = PostgresReadinessProbe(
        FakeEngine(
            connect_error=RuntimeError(
                "postgresql://secret@private.example/riftcoach"
            )
        ),
        revision_reader=lambda _connection: ("ignored", "ignored"),
    )

    result = probe.check()

    assert result.is_ready is False
    assert result.code == "database_unavailable"
    assert "private.example" not in repr(result)
    assert "secret" not in repr(result)


def test_production_without_auth_provider_starts_but_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("app.api.composition.build_engine", lambda _settings: engine)
    monkeypatch.setattr(
        "app.api.composition.build_session_factory",
        lambda _engine: (lambda: None),
    )
    app = create_composed_app(
        environment={
            **VALID_ENV,
            "RIFTCOACH_API_PROFILE": "production",
            "RIFTCOACH_RUNS_ROOT": str(tmp_path),
        }
    )

    with TestClient(app) as http:
        assert http.get("/health/live").status_code == 200
        assert http.get("/health/ready").json()["code"] == (
            "actor_context_unavailable"
        )
        response = http.post(
            "/reviews/recent",
            headers={"Idempotency-Key": "request-1"},
            json={"riot_id": "DemoPlayer#TEST"},
        )

    assert response.status_code == 503
    assert response.json() == {"code": "service_unavailable"}


def test_static_owner_cannot_be_enabled_for_production_profile() -> None:
    with pytest.raises(ValueError, match="local/test"):
        StaticActorContextProvider(owner_id="unsafe-owner", profile="production")
