from __future__ import annotations

import io
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects.postgresql import JSONB

from app.persistence.task_event_record import ReviewTaskEventRecord
from app.persistence.task_record import ReviewTaskRecord
from app.tasks.models import TaskStatus
from app.tasks.reliable_runtime import (
    TaskLifecycleEvent,
    TaskLifecycleEventKind,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
HEAD = "0010_reliable_runtime_core"


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def test_reliable_runtime_metadata_and_head_are_explicit() -> None:
    task = ReviewTaskRecord.__table__
    event = ReviewTaskEventRecord.__table__
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()

    assert head == HEAD
    assert event.metadata is task.metadata
    assert event.name == "review_task_events"
    assert event.c.checkpoint_reference.type.__class__ is JSONB
    assert event.c.checkpoint_reference.type.none_as_null is True
    assert task.c.checkpoint_reference.type.none_as_null is True
    lifecycle = next(
        constraint
        for constraint in task.constraints
        if constraint.name == "ck_review_tasks_reliable_lifecycle_shape"
    )
    assert "terminal_reason IS NOT NULL AND lease_generation >= 0" in str(
        lifecycle.sqltext
    )
    assert event.c.occurred_at.type.timezone is True
    assert event.c.event_cursor.identity is not None
    assert task.c.status.type.length == 24

    assert {
        "lease_generation",
        "lease_token",
        "lease_expires_at",
        "heartbeat_at",
        "cancel_request_id",
        "cancel_requested_at",
        "cancel_reason",
        "checkpoint_sequence",
        "checkpoint_reference",
        "recovery_count",
        "recovery_required_at",
        "recovery_reason",
    } <= set(task.c.keys())
    assert {
        "pk_review_task_events",
        "uq_review_task_events_event_identity",
        "uq_review_task_events_task_sequence",
        "uq_review_task_events_task_operation",
        "fk_review_task_events_task_identity",
        "ck_review_task_events_event_identity_format",
        "ck_review_task_events_event_kind_allowed",
        "ck_review_task_events_status_allowed",
        "ck_review_task_events_checkpoint_bound",
    } <= {constraint.name for constraint in event.constraints}
    assert {
        "ix_review_task_events_owner_cursor",
        "ix_review_task_events_task_cursor",
    } <= {index.name for index in event.indexes}
    assert "ix_review_tasks_expired_lease" in {
        index.name for index in task.indexes
    }


def test_reliable_runtime_offline_sql_has_stable_schema_and_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach"
    monkeypatch.setenv("DATABASE_URL", url)
    output = io.StringIO()
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()

    assert "ADD COLUMN lease_generation BIGINT DEFAULT '0' NOT NULL" in sql
    assert "ADD COLUMN lease_token VARCHAR(64)" in sql
    assert "ADD COLUMN checkpoint_reference JSONB" in sql
    assert "CREATE TABLE review_task_events" in sql
    assert "CONSTRAINT ck_review_tasks_reliable_lifecycle_shape" in sql
    assert "CONSTRAINT fk_review_task_events_task_identity" in sql
    assert "CREATE INDEX ix_review_tasks_expired_lease" in sql
    assert "CREATE INDEX ix_review_task_events_owner_cursor" in sql
    assert "INSERT INTO review_task_events" in sql
    assert "snapshot_imported" in sql
    assert "snapshot-import-0010" in sql


def test_reliable_runtime_offline_downgrade_uses_existing_constraint_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach"
    monkeypatch.setenv("DATABASE_URL", url)
    output = io.StringIO()
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.downgrade(
        config,
        f"{HEAD}:0009_owner_data_lifecycle",
        sql=True,
    )
    sql = output.getvalue()

    assert (
        "DROP CONSTRAINT ck_review_tasks_timestamp_order" in sql
    )
    assert "ck_review_tasks_ck_review_tasks_" not in sql


@pytest.fixture()
def postgres_migration_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[str]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")

    monkeypatch.setenv("DATABASE_URL", url)
    config = alembic_config()
    command.downgrade(config, "base")
    try:
        yield url
    finally:
        command.downgrade(config, "base")


def test_0010_migrates_running_legacy_task_to_recovery_required_and_snapshots(
    postgres_migration_database: str,
) -> None:
    config = alembic_config()
    command.upgrade(config, "0009_owner_data_lifecycle")
    engine = sa.create_engine(postgres_migration_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO review_tasks (
                        task_id, run_id, task_kind, schema_version, owner_id,
                        idempotency_key, request_fingerprint, request_payload,
                        status, worker_id, claimed_at, updated_at
                    ) VALUES (
                        '81000000-0000-4000-8000-000000000010',
                        'review_legacy_running_0010', 'recent_review', '1.0',
                        'owner-legacy-0010', 'idem-legacy-0010', :fingerprint,
                        CAST(:payload AS JSONB), 'running', 'worker-legacy-0010',
                        now(), now()
                    )
                    """
                ),
                {"fingerprint": "a" * 64, "payload": "{}"},
            )

        command.upgrade(config, "head")
        inspector = sa.inspect(engine)
        assert "review_task_events" in inspector.get_table_names()
        with engine.begin() as connection:
            task = connection.execute(
                sa.text(
                    """
                    SELECT status, lease_generation, lease_token,
                           recovery_required_at, recovery_reason
                    FROM review_tasks
                    WHERE run_id = 'review_legacy_running_0010'
                    """
                )
            ).one()
            lifecycle_event = connection.execute(
                sa.text(
                    """
                    SELECT event_cursor, event_kind, status_after,
                           lease_generation, operation_identity, task_sequence,
                           event_identity, task_id, run_id, owner_id, worker_id,
                           reason, occurred_at
                    FROM review_task_events
                    WHERE run_id = 'review_legacy_running_0010'
                    """
                )
            ).one()

        assert task.status == "recovery_required"
        assert task.lease_generation == 1
        assert task.lease_token is None
        assert task.recovery_required_at is not None
        assert task.recovery_reason == "migration_requires_recovery"
        assert lifecycle_event.event_kind == "snapshot_imported"
        assert lifecycle_event.status_after == "recovery_required"
        assert lifecycle_event.lease_generation == 1
        assert lifecycle_event.operation_identity == "snapshot-import-0010"
        assert lifecycle_event.task_sequence == 1
        assert len(lifecycle_event.event_identity) == 64
        expected_event = TaskLifecycleEvent.create(
            event_cursor=lifecycle_event.event_cursor,
            task_sequence=1,
            task_id=lifecycle_event.task_id,
            run_id=lifecycle_event.run_id,
            owner_id=lifecycle_event.owner_id,
            event_kind=TaskLifecycleEventKind.SNAPSHOT_IMPORTED,
            status_after=TaskStatus.RECOVERY_REQUIRED,
            lease_generation=1,
            worker_id=lifecycle_event.worker_id,
            operation_identity="snapshot-import-0010",
            reason=lifecycle_event.reason,
            occurred_at=lifecycle_event.occurred_at,
        )
        assert lifecycle_event.event_identity == expected_event.event_identity

        command.downgrade(config, "0009_owner_data_lifecycle")
        inspector = sa.inspect(engine)
        assert "review_task_events" not in inspector.get_table_names()
        assert "lease_generation" not in {
            column["name"] for column in inspector.get_columns("review_tasks")
        }
        command.upgrade(config, "head")
        assert "review_task_events" in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_0010_downgrade_never_resurrects_preclaim_cancel_as_queued(
    postgres_migration_database: str,
) -> None:
    config = alembic_config()
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO review_tasks (
                        task_id, run_id, task_kind, schema_version, owner_id,
                        idempotency_key, request_fingerprint, request_payload,
                        status, cancel_request_id, cancel_requested_at,
                        cancel_reason, finished_at, terminal_reason
                    ) VALUES (
                        '81000000-0000-4000-8000-000000000011',
                        'review_cancelled_downgrade_0010', 'recent_review',
                        '1.0', 'owner-cancelled-0010', 'idem-cancelled-0010',
                        :fingerprint, CAST(:payload AS JSONB), 'cancelled',
                        'cancel-before-claim', now(), 'user_requested', now(),
                        'user_requested'
                    )
                    """
                ),
                {"fingerprint": "b" * 64, "payload": "{}"},
            )

        command.downgrade(config, "0009_owner_data_lifecycle")
        with engine.begin() as connection:
            task = connection.execute(
                sa.text(
                    """
                    SELECT status, worker_id, claimed_at, finished_at,
                           terminal_reason
                    FROM review_tasks
                    WHERE run_id = 'review_cancelled_downgrade_0010'
                    """
                )
            ).one()

        assert task.status == "failed"
        assert task.worker_id == "migration-0010-downgrade"
        assert task.claimed_at is not None
        assert task.finished_at >= task.claimed_at
        assert task.terminal_reason == "cancelled_downgrade"
    finally:
        engine.dispose()
