from __future__ import annotations

import io
import json
import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.persistence.task_record import ReviewTaskRecord


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"


def config() -> Config:
    value = Config(str(ROOT / "alembic.ini"))
    value.set_main_option("script_location", str(ROOT / "migrations"))
    return value


def test_review_identity_revision_and_orm_metadata_are_frozen() -> None:
    head = ScriptDirectory.from_config(config()).get_current_head()
    assert head == "0009_owner_data_lifecycle"
    assert len(head) <= 32

    table = ReviewTaskRecord.__table__
    assert {
        "conversation_id",
        "relationship_id",
        "player_subject_id",
        "relationship_role",
    } <= set(table.c.keys())
    constraints = {item.name for item in table.constraints}
    indexes = {item.name for item in table.indexes}
    assert {
        "ck_review_tasks_schema_version_allowed",
        "ck_review_tasks_schema_identity_shape",
        "ck_review_tasks_conversation_role_allowed",
        "fk_review_tasks_conversation_identity",
    } <= constraints
    assert {
        "ix_review_tasks_conversation_id",
        "ix_review_tasks_relationship_id",
        "ix_review_tasks_player_subject_id",
    } <= indexes


def test_offline_sql_contains_identity_shape_fk_indexes_and_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach",
    )
    output = io.StringIO()
    alembic = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    alembic.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(alembic, "head", sql=True)
    sql = output.getvalue()

    assert "ADD COLUMN conversation_id UUID" in sql
    assert "CONSTRAINT ck_review_tasks_schema_identity_shape" in sql
    assert "CONSTRAINT fk_review_tasks_conversation_identity" in sql
    assert "CREATE INDEX ix_review_tasks_conversation_id" in sql
    assert "CREATE FUNCTION riftcoach_guard_review_task_identity" in sql
    assert "CREATE TRIGGER trg_review_tasks_guard_identity" in sql


@pytest.fixture()
def postgres_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL "
            "review identity evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")
    monkeypatch.setenv("DATABASE_URL", url)
    command.downgrade(config(), "base")
    try:
        yield url
    finally:
        command.downgrade(config(), "base")


def seed_conversation(connection: sa.Connection) -> dict[str, object]:
    values: dict[str, object] = {
        "owner_id": "owner-migration-v2",
        "player_subject_id": uuid.uuid4(),
        "relationship_id": uuid.uuid4(),
        "conversation_id": uuid.uuid4(),
    }
    connection.execute(
        sa.text(
            "INSERT INTO player_subjects (player_subject_id, game, puuid, "
            "current_routing_region) VALUES (:player_subject_id, 'lol', "
            ":puuid, 'asia')"
        ),
        {**values, "puuid": f"PUUID_{values['player_subject_id']}"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO owner_player_relationships (relationship_id, owner_id, "
            "player_subject_id, relationship_role, verification_status) VALUES "
            "(:relationship_id, :owner_id, :player_subject_id, 'self', "
            "'unverified_claim')"
        ),
        values,
    )
    connection.execute(
        sa.text(
            "INSERT INTO conversations (conversation_id, owner_id, relationship_id, "
            "player_subject_id, relationship_role, idempotency_key, "
            "request_fingerprint) VALUES (:conversation_id, :owner_id, "
            ":relationship_id, :player_subject_id, 'self', 'conversation-key', "
            ":fingerprint)"
        ),
        {**values, "fingerprint": "a" * 64},
    )
    return values


def insert_task(
    connection: sa.Connection,
    *,
    schema_version: str,
    values: dict[str, object],
    include_identity: bool,
) -> uuid.UUID:
    task_id = uuid.uuid4()
    identity_columns = (
        ", conversation_id, relationship_id, player_subject_id, relationship_role"
        if include_identity
        else ""
    )
    identity_values = (
        ", :conversation_id, :relationship_id, :player_subject_id, 'self'"
        if include_identity
        else ""
    )
    connection.execute(
        sa.text(
            "INSERT INTO review_tasks (task_id, run_id, task_kind, schema_version, "
            "owner_id, idempotency_key, request_fingerprint, request_payload"
            f"{identity_columns}) VALUES (:task_id, :run_id, 'recent_review', "
            ":schema_version, :owner_id, :idempotency_key, :fingerprint, "
            f"CAST(:payload AS JSONB){identity_values})"
        ),
        {
            **values,
            "task_id": task_id,
            "run_id": f"run_{task_id.hex}",
            "schema_version": schema_version,
            "idempotency_key": f"key_{task_id.hex}",
            "fingerprint": "b" * 64,
            "payload": json.dumps({"count": 5, "queue": 420, "focus": "overall"}),
        },
    )
    return task_id


def test_real_schema_accepts_legacy_and_complete_v2_but_rejects_partial_or_rebind(
    postgres_database: str,
) -> None:
    command.upgrade(config(), "head")
    engine = sa.create_engine(postgres_database)
    try:
        with engine.begin() as connection:
            values = seed_conversation(connection)
            legacy_id = insert_task(
                connection,
                schema_version="1.0",
                values=values,
                include_identity=False,
            )
            v2_id = insert_task(
                connection,
                schema_version="2.0",
                values=values,
                include_identity=True,
            )
        with engine.connect() as connection:
            rows = connection.execute(
                sa.text(
                    "SELECT task_id, schema_version, conversation_id FROM review_tasks "
                    "WHERE task_id IN (:legacy_id, :v2_id) ORDER BY schema_version"
                ),
                {"legacy_id": legacy_id, "v2_id": v2_id},
            ).all()
        assert rows[0].schema_version == "1.0"
        assert rows[0].conversation_id is None
        assert rows[1].schema_version == "2.0"
        assert rows[1].conversation_id == values["conversation_id"]

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                insert_task(
                    connection,
                    schema_version="2.0",
                    values={**values, "relationship_id": None},
                    include_identity=True,
                )
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE review_tasks SET conversation_id = :other "
                        "WHERE task_id = :task_id"
                    ),
                    {"other": uuid.uuid4(), "task_id": v2_id},
                )
    finally:
        engine.dispose()


def test_0004_downgrade_preserves_legacy_review_table(
    postgres_database: str,
) -> None:
    command.upgrade(config(), "head")
    command.downgrade(config(), "0003_conversation_messages")
    engine = sa.create_engine(postgres_database)
    try:
        columns = {
            item["name"] for item in sa.inspect(engine).get_columns("review_tasks")
        }
        assert "review_tasks" in sa.inspect(engine).get_table_names()
        assert "conversation_id" not in columns
    finally:
        engine.dispose()
    command.upgrade(config(), "head")
