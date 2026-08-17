from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import yaml
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.persistence.config import (
    DatabaseConfigurationError,
    DatabaseSettings,
    load_database_settings,
)
from app.persistence.database import Base, build_engine, build_session_factory
from app.persistence.task_record import ReviewTaskRecord


VALID_URL = "postgresql+psycopg://riftcoach:local-secret@localhost:5432/riftcoach"
ROOT = Path(__file__).resolve().parents[1]


def test_database_settings_load_from_explicit_environment() -> None:
    settings = load_database_settings(
        {
            "DATABASE_URL": VALID_URL,
            "DATABASE_POOL_SIZE": "7",
            "DATABASE_POOL_TIMEOUT_SECONDS": "11",
        }
    )

    assert settings == DatabaseSettings(
        url=VALID_URL,
        pool_size=7,
        pool_timeout_s=11,
    )
    assert "local-secret" not in repr(settings)
    assert VALID_URL not in repr(settings)


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"DATABASE_URL": ""},
        {"DATABASE_URL": "   "},
    ],
)
def test_database_settings_fail_closed_when_url_is_missing(
    environment: dict[str, str],
) -> None:
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is required"):
        load_database_settings(environment)


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///riftcoach.db",
        "postgresql://user:password@localhost/riftcoach",
        "postgresql+psycopg2://user:password@localhost/riftcoach",
        "mysql+pymysql://user:password@localhost/riftcoach",
    ],
)
def test_database_settings_require_postgresql_psycopg_without_leaking_url(
    url: str,
) -> None:
    with pytest.raises(DatabaseConfigurationError) as exc_info:
        DatabaseSettings(url=url)

    message = str(exc_info.value)
    assert "postgresql+psycopg" in message
    assert url not in message
    assert "password" not in message


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pool_size", 0),
        ("pool_size", -1),
        ("pool_size", True),
        ("pool_timeout_s", 0),
        ("pool_timeout_s", -1),
        ("pool_timeout_s", False),
    ],
)
def test_database_settings_reject_invalid_pool_values(field: str, value: object) -> None:
    values: dict[str, object] = {"url": VALID_URL, field: value}

    with pytest.raises(DatabaseConfigurationError, match=field):
        DatabaseSettings(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DATABASE_POOL_SIZE", "not-an-int"),
        ("DATABASE_POOL_TIMEOUT_SECONDS", "1.5"),
    ],
)
def test_database_settings_reject_non_integer_environment_values(
    name: str,
    value: str,
) -> None:
    with pytest.raises(DatabaseConfigurationError, match=name):
        load_database_settings({"DATABASE_URL": VALID_URL, name: value})


def test_engine_and_session_factory_are_created_without_opening_a_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("Engine construction must not connect to PostgreSQL")

    monkeypatch.setattr("psycopg.connect", forbidden_connect)
    settings = DatabaseSettings(url=VALID_URL, pool_size=3, pool_timeout_s=9)

    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    assert isinstance(engine, Engine)
    assert engine.driver == "psycopg"
    assert engine.pool.size() == 3
    assert engine.pool.timeout() == 9
    assert engine.pool._pre_ping is True

    session = session_factory()
    assert isinstance(session, Session)
    assert session.bind is engine
    assert session.expire_on_commit is False
    session.close()
    engine.dispose()


def test_review_task_metadata_has_foundation_identity_and_postgres_types() -> None:
    table = ReviewTaskRecord.__table__

    assert table.metadata is Base.metadata
    assert table.name == "review_tasks"
    assert table.c.task_id.type.python_type is uuid.UUID
    assert table.c.run_id.unique is True
    assert table.c.request_payload.type.__class__.__name__ == "JSONB"
    assert table.c.trace_reference.type.__class__.__name__ == "JSONB"
    assert table.c.receipt_reference.type.__class__.__name__ == "JSONB"
    assert table.c.artifact_reference.type.__class__.__name__ == "JSONB"
    assert table.c.created_at.type.timezone is True
    assert table.c.updated_at.type.timezone is True
    assert table.c.claimed_at.type.timezone is True
    assert table.c.finished_at.type.timezone is True

    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert {
        "pk_review_tasks",
        "uq_review_tasks_run_id",
        "uq_review_tasks_owner_id_idempotency_key",
        "ck_review_tasks_status_allowed",
        "ck_review_tasks_publication_status_allowed",
        "ck_review_tasks_request_fingerprint_format",
        "ck_review_tasks_lifecycle_shape",
        "ck_review_tasks_timestamp_order",
    } <= constraint_names
    assert {
        "ix_review_tasks_claim",
        "ix_review_tasks_owner_history",
    } <= index_names


def test_compose_and_ci_define_a_real_postgresql_migration_gate() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    )

    postgres = compose["services"]["postgres"]
    assert postgres["image"] == "postgres:17-alpine"
    assert "pg_isready" in " ".join(postgres["healthcheck"]["test"])

    jobs = workflow["jobs"]
    assert "pytest" in jobs
    assert "postgres-migrations" in jobs
    migration_job = jobs["postgres-migrations"]
    assert migration_job["services"]["postgres"]["image"] == "postgres:17-alpine"
    assert migration_job["env"]["DATABASE_URL"].startswith("postgresql+psycopg://")
    assert migration_job["env"]["RIFTCOACH_TEST_DATABASE_URL"].startswith(
        "postgresql+psycopg://"
    )

    serialized_job = yaml.safe_dump(migration_job)
    assert "sqlite" not in serialized_job.lower()
    assert "RIOT_API_KEY" not in serialized_job
    assert "LLM_API_KEY" not in serialized_job
