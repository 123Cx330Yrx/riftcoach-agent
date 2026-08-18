from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.database import build_engine, build_session_factory
from app.persistence.config import DatabaseSettings
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.task_repository import PostgresTaskRepository, _record_to_task
from app.tasks.models import (
    PendingReviewTask,
    TaskCapacityPolicy,
    TaskRepositoryCreateDisposition,
    TaskStatus,
)
from app.tasks.ports import TaskRepositoryError


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
NOW = datetime(2026, 8, 18, 3, 0, 0, tzinfo=timezone.utc)


@contextmanager
def migrated_repository() -> Iterator[
    tuple[PostgresTaskRepository, sessionmaker[Session]]
]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL repository evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = build_engine(DatabaseSettings(url=url))
    factory = build_session_factory(engine)
    try:
        yield PostgresTaskRepository(factory), factory
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def pending(
    number: int,
    *,
    owner_id: str = "owner-1",
    key: str | None = None,
    fingerprint: str | None = None,
) -> PendingReviewTask:
    return PendingReviewTask(
        task_id=UUID(f"20000000-0000-4000-8000-{number:012d}"),
        run_id=f"review_repository_{number}",
        owner_id=owner_id,
        idempotency_key=key or f"request-{number}",
        request_fingerprint=fingerprint or f"{number:064x}",
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        created_at=NOW + timedelta(seconds=number),
    )


def test_record_mapping_returns_strict_task_without_database() -> None:
    source_payload = {
        "riot_id": "DemoPlayer#TEST",
        "count": 10,
        "queue": 420,
        "focus": "overall",
    }
    record = ReviewTaskRecord(
        task_id=UUID("20000000-0000-4000-8000-000000000001"),
        run_id="review_repository_mapping",
        task_kind="recent_review",
        schema_version="1.0",
        owner_id="owner-1",
        idempotency_key="request-1",
        request_fingerprint="1" * 64,
        request_payload=source_payload,
        status=TaskStatus.QUEUED.value,
        worker_id=None,
        created_at=NOW,
        updated_at=NOW,
        claimed_at=None,
        finished_at=None,
        terminal_reason=None,
        publication_status=None,
        report_available=False,
        trace_reference=None,
        receipt_reference=None,
        artifact_reference=None,
    )

    task = _record_to_task(record)

    assert task.task_id == record.task_id
    assert task.status is TaskStatus.QUEUED
    assert task.request_payload == source_payload
    assert task.request_payload is not source_payload


def test_repository_creates_and_replays_original_identity_atomically() -> None:
    with migrated_repository() as (repository, factory):
        original = pending(1, key="same-request", fingerprint="a" * 64)
        alternate = pending(2, key="same-request", fingerprint="a" * 64)

        created = repository.create_or_replay(
            original,
            capacity=TaskCapacityPolicy(),
        )
        replayed = repository.create_or_replay(
            alternate,
            capacity=TaskCapacityPolicy(),
        )

        assert created.disposition is TaskRepositoryCreateDisposition.CREATED
        assert replayed.disposition is TaskRepositoryCreateDisposition.REPLAYED
        assert created.task is not None
        assert replayed.task is not None
        assert replayed.task.task_id == original.task_id
        assert replayed.task.run_id == original.run_id
        assert replayed.task.request_payload == original.request_payload
        assert replayed.task.created_at == original.created_at
        assert replayed.task.status is TaskStatus.QUEUED

        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ReviewTaskRecord)
            ) == 1


def test_repository_idempotency_conflict_and_owner_scope_do_not_mutate_row() -> None:
    with migrated_repository() as (repository, factory):
        original = pending(1, key="same-request", fingerprint="a" * 64)
        repository.create_or_replay(original, capacity=TaskCapacityPolicy())

        conflict = repository.create_or_replay(
            pending(2, key="same-request", fingerprint="b" * 64),
            capacity=TaskCapacityPolicy(),
        )
        other_owner = repository.create_or_replay(
            pending(
                3,
                owner_id="owner-2",
                key="same-request",
                fingerprint="b" * 64,
            ),
            capacity=TaskCapacityPolicy(),
        )

        assert (
            conflict.disposition
            is TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
        )
        assert conflict.task is None
        assert other_owner.disposition is TaskRepositoryCreateDisposition.CREATED
        assert repository.get_by_task_id(
            owner_id="owner-1",
            task_id=original.task_id,
        ) is not None
        assert repository.get_by_task_id(
            owner_id="owner-2",
            task_id=original.task_id,
        ) is None
        assert repository.get_by_run_id(
            owner_id="owner-2",
            run_id=original.run_id,
        ) is None

        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ReviewTaskRecord)
            ) == 2


def test_repository_capacity_ignores_replay_and_terminal_rows() -> None:
    policy = TaskCapacityPolicy(owner_active_limit=1, global_active_limit=2)
    with migrated_repository() as (repository, factory):
        first = pending(1, key="one", fingerprint="a" * 64)
        repository.create_or_replay(first, capacity=policy)

        replay = repository.create_or_replay(
            pending(2, key="one", fingerprint="a" * 64),
            capacity=policy,
        )
        owner_full = repository.create_or_replay(
            pending(3, key="two", fingerprint="b" * 64),
            capacity=policy,
        )
        assert replay.disposition is TaskRepositoryCreateDisposition.REPLAYED
        assert (
            owner_full.disposition
            is TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED
        )

        claimed = first.created_at + timedelta(seconds=1)
        finished = first.created_at + timedelta(seconds=2)
        with factory.begin() as session:
            session.execute(
                sa.update(ReviewTaskRecord)
                .where(ReviewTaskRecord.task_id == first.task_id)
                .values(
                    status="failed",
                    worker_id="worker-1",
                    updated_at=finished,
                    claimed_at=claimed,
                    finished_at=finished,
                    terminal_reason="worker_interrupted",
                )
            )

        replacement = repository.create_or_replay(
            pending(3, key="two", fingerprint="b" * 64),
            capacity=policy,
        )
        other_owner = repository.create_or_replay(
            pending(4, owner_id="owner-2", key="three", fingerprint="c" * 64),
            capacity=policy,
        )
        global_full = repository.create_or_replay(
            pending(5, owner_id="owner-3", key="four", fingerprint="d" * 64),
            capacity=policy,
        )

        assert replacement.disposition is TaskRepositoryCreateDisposition.CREATED
        assert other_owner.disposition is TaskRepositoryCreateDisposition.CREATED
        assert (
            global_full.disposition
            is TaskRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED
        )


def test_repository_rolls_back_identity_collision_and_remains_usable() -> None:
    with migrated_repository() as (repository, factory):
        original = pending(1)
        repository.create_or_replay(original, capacity=TaskCapacityPolicy())
        collision = pending(2).model_copy(
            update={"task_id": original.task_id}
        )

        with pytest.raises(TaskRepositoryError) as exc_info:
            repository.create_or_replay(
                collision,
                capacity=TaskCapacityPolicy(),
            )

        assert str(exc_info.value) == "task_repository_unavailable"
        assert "duplicate" not in repr(exc_info.value).lower()
        assert repository.get_by_task_id(
            owner_id=original.owner_id,
            task_id=original.task_id,
        ) is not None
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ReviewTaskRecord)
            ) == 1


def test_concurrent_same_key_creates_exactly_one_row_and_replays_one() -> None:
    with migrated_repository() as (repository, factory):
        barrier = Barrier(2)

        def create(candidate: PendingReviewTask):
            barrier.wait(timeout=5)
            return repository.create_or_replay(
                candidate,
                capacity=TaskCapacityPolicy(),
            )

        candidates = (
            pending(1, key="concurrent", fingerprint="e" * 64),
            pending(2, key="concurrent", fingerprint="e" * 64),
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(create, candidates))

        assert {result.disposition for result in results} == {
            TaskRepositoryCreateDisposition.CREATED,
            TaskRepositoryCreateDisposition.REPLAYED,
        }
        assert len({result.task.task_id for result in results if result.task}) == 1
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ReviewTaskRecord)
            ) == 1
