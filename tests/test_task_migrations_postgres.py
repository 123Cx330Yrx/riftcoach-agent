from __future__ import annotations

import os
import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.dialects.postgresql import JSONB, UUID


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"


@pytest.fixture()
def postgres_migration_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL migration evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")

    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.downgrade(config, "base")
    try:
        yield url
    finally:
        command.downgrade(config, "base")


def test_initial_migration_creates_postgresql_task_schema(
    postgres_migration_database: str,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")

    engine = sa.create_engine(postgres_migration_database)
    try:
        inspector = sa.inspect(engine)
        assert "review_tasks" in inspector.get_table_names()

        columns = {
            column["name"]: column
            for column in inspector.get_columns("review_tasks")
        }
        assert isinstance(columns["task_id"]["type"], UUID)
        assert isinstance(columns["request_payload"]["type"], JSONB)
        assert isinstance(columns["trace_reference"]["type"], JSONB)
        assert isinstance(columns["receipt_reference"]["type"], JSONB)
        assert isinstance(columns["artifact_reference"]["type"], JSONB)
        for timestamp_name in (
            "created_at",
            "updated_at",
            "claimed_at",
            "finished_at",
        ):
            assert columns[timestamp_name]["type"].timezone is True

        primary_key = inspector.get_pk_constraint("review_tasks")
        unique_names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("review_tasks")
        }
        check_names = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("review_tasks")
        }
        index_names = {
            index["name"] for index in inspector.get_indexes("review_tasks")
        }

        assert primary_key["name"] == "pk_review_tasks"
        assert {
            "uq_review_tasks_run_id",
            "uq_review_tasks_owner_id_idempotency_key",
        } <= unique_names
        assert {
            "ck_review_tasks_status_allowed",
            "ck_review_tasks_publication_status_allowed",
            "ck_review_tasks_request_fingerprint_format",
            "ck_review_tasks_lifecycle_shape",
            "ck_review_tasks_timestamp_order",
        } <= check_names
        assert {
            "ix_review_tasks_claim",
            "ix_review_tasks_owner_history",
        } <= index_names
    finally:
        engine.dispose()


def test_initial_migration_downgrades_and_upgrades_cleanly(
    postgres_migration_database: str,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = sa.create_engine(postgres_migration_database)
    try:
        assert "review_tasks" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_initial_migration_enforces_status_and_round_trips_postgres_types(
    postgres_migration_database: str,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)

    valid_values = {
        "task_id": uuid.uuid4(),
        "run_id": "run_foundation_round_trip",
        "task_kind": "recent_review",
        "schema_version": "1.0",
        "owner_id": "owner_foundation",
        "idempotency_key": "idem_foundation_round_trip",
        "request_fingerprint": "a" * 64,
        "request_payload": json.dumps({"artifact": "body-free-reference"}),
    }
    insert_sql = sa.text(
        """
        INSERT INTO review_tasks (
            task_id, run_id, task_kind, schema_version, owner_id,
            idempotency_key, request_fingerprint, request_payload
        ) VALUES (
            :task_id, :run_id, :task_kind, :schema_version, :owner_id,
            :idempotency_key, :request_fingerprint, CAST(:request_payload AS JSONB)
        )
        """
    )

    try:
        with engine.begin() as connection:
            connection.execute(insert_sql, valid_values)
            row = connection.execute(
                sa.text(
                    "SELECT request_payload, created_at, updated_at, status "
                    "FROM review_tasks WHERE task_id = :task_id"
                ),
                {"task_id": valid_values["task_id"]},
            ).one()

        assert row.request_payload == {"artifact": "body-free-reference"}
        assert row.created_at.tzinfo is not None
        assert row.updated_at.tzinfo is not None
        assert row.status == "queued"

        invalid_values = {
            **valid_values,
            "task_id": uuid.uuid4(),
            "run_id": "run_invalid_status",
            "idempotency_key": "idem_invalid_status",
        }
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(insert_sql, invalid_values)
                connection.execute(
                    sa.text(
                        "UPDATE review_tasks SET status = 'cancelled' "
                        "WHERE task_id = :task_id"
                    ),
                    {"task_id": invalid_values["task_id"]},
                )
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        assert "review_tasks" in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()
