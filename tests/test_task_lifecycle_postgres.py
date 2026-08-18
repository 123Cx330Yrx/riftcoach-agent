from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_repository import PostgresTaskRepository
from app.tasks.deletion import (
    FileRunDataCleaner,
    TaskDeleteDisposition,
    TaskDeletionService,
)
from app.tasks.models import PendingReviewTask, TaskCapacityPolicy, TaskStatus
from app.tasks.models import (
    TaskDeleteDisposition,
    TaskRepositoryDeleteDisposition,
    TaskRepositoryDeleteResult,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 18, 14, 0, tzinfo=timezone.utc)


@contextmanager
def migrated_repository() -> Iterator[PostgresTaskRepository]:
    url = os.getenv("RIFTCOACH_TEST_DATABASE_URL")
    if not url:
        pytest.skip("real PostgreSQL lifecycle evidence runs in CI")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = build_engine(DatabaseSettings(url=url))
    factory = build_session_factory(engine)
    try:
        yield PostgresTaskRepository(factory)
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


def pending(number: int = 1) -> PendingReviewTask:
    return PendingReviewTask(
        task_id=UUID(f"40000000-0000-4000-8000-{number:012d}"),
        run_id=f"review_delete_{number}",
        owner_id="owner-1",
        idempotency_key=f"delete-{number}",
        request_fingerprint=f"{number:064x}",
        request_payload={"riot_id": "DemoPlayer#TEST", "count": 10},
        created_at=NOW,
    )


class FakeDeleteRepository:
    def __init__(self, result: TaskRepositoryDeleteResult) -> None:
        self.result = result
        self.calls: list[tuple[str, UUID]] = []

    def delete_terminal(self, *, owner_id: str, task_id: UUID):
        self.calls.append((owner_id, task_id))
        return self.result


class FakeCleaner:
    def __init__(self, cleaned: bool) -> None:
        self.cleaned = cleaned
        self.calls: list[str] = []

    def cleanup(self, run_id: str) -> bool:
        self.calls.append(run_id)
        return self.cleaned


def test_cleanup_failure_keeps_resource_hidden_and_creates_retry_marker(
    tmp_path: Path,
) -> None:
    task_id = UUID("40000000-0000-4000-8000-000000000001")
    repository = FakeDeleteRepository(
        TaskRepositoryDeleteResult(
            disposition=TaskRepositoryDeleteDisposition.DELETED,
            run_id="review_delete_1",
        )
    )
    cleaner = FakeCleaner(cleaned=False)
    service = TaskDeletionService(repository=repository, cleaner=cleaner)

    result = service.delete(owner_id="owner-1", task_id=task_id)

    assert result.disposition is TaskDeleteDisposition.CLEANUP_PENDING
    assert cleaner.calls == ["review_delete_1"]
    assert repository.calls == [("owner-1", task_id)]


def test_repeated_missing_delete_is_idempotent_and_never_calls_cleaner() -> None:
    task_id = UUID("40000000-0000-4000-8000-000000000002")
    repository = FakeDeleteRepository(
        TaskRepositoryDeleteResult(
            disposition=TaskRepositoryDeleteDisposition.NOT_FOUND,
        )
    )
    cleaner = FakeCleaner(cleaned=True)

    result = TaskDeletionService(repository=repository, cleaner=cleaner).delete(
        owner_id="owner-1",
        task_id=task_id,
    )

    assert result.disposition is TaskDeleteDisposition.ALREADY_HIDDEN
    assert cleaner.calls == []


def test_file_cleaner_failure_writes_only_retryable_internal_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "review_cleanup_failure"
    run_dir.mkdir()
    (run_dir / "private-report.md").write_text("private", encoding="utf-8")
    cleaner = FileRunDataCleaner(tmp_path, clock=lambda: NOW)

    def fail_rmtree(_path):
        raise OSError("private path and secret")

    monkeypatch.setattr("app.tasks.deletion.shutil.rmtree", fail_rmtree)

    assert cleaner.cleanup("review_cleanup_failure") is False
    marker = tmp_path / ".deletion_compensation" / "review_cleanup_failure.json"
    assert marker.is_file()
    text = marker.read_text(encoding="utf-8")
    assert "review_cleanup_failure" in text
    assert "private path" not in text
    assert "secret" not in text
    assert cleaner.has_pending("review_cleanup_failure")


def test_active_task_delete_is_not_cancel_and_is_safe_conflict() -> None:
    with migrated_repository() as repository:
        created = repository.create_or_replay(
            pending(), capacity=TaskCapacityPolicy()
        ).task
        assert created is not None
        claimed = repository.claim_next(worker_id="worker-1", now=NOW + timedelta(seconds=1))
        assert claimed is not None
        service = TaskDeletionService(
            repository=repository,
            cleaner=FileRunDataCleaner(Path("tmp")),
            clock=lambda: NOW + timedelta(seconds=2),
        )

        result = service.delete(owner_id="owner-1", task_id=created.task_id)

        assert result.disposition is TaskDeleteDisposition.ACTIVE_CONFLICT
        assert repository.get_by_task_id(owner_id="owner-1", task_id=created.task_id) is not None


def test_terminal_delete_hides_sql_row_before_cleaning_run_data(tmp_path: Path) -> None:
    with migrated_repository() as repository:
        created = repository.create_or_replay(
            pending(), capacity=TaskCapacityPolicy()
        ).task
        assert created is not None
        claimed = repository.claim_next(worker_id="worker-1", now=NOW + timedelta(seconds=1))
        assert claimed is not None
        assert repository.fail(
            task_id=created.task_id,
            worker_id="worker-1",
            reason="worker_execution_failed",
        )
        run_dir = tmp_path / created.run_id
        run_dir.mkdir()
        (run_dir / "api_run_receipt.json").write_text("private", encoding="utf-8")
        service = TaskDeletionService(
            repository=repository,
            cleaner=FileRunDataCleaner(tmp_path),
            clock=lambda: NOW + timedelta(seconds=2),
        )

        result = service.delete(owner_id="owner-1", task_id=created.task_id)

        assert result.disposition is TaskDeleteDisposition.DELETED
        assert repository.get_by_task_id(owner_id="owner-1", task_id=created.task_id) is None
        assert not run_dir.exists()


def test_postgres_owner_capacity_race_cannot_create_two_active_tasks() -> None:
    with migrated_repository() as repository:
        policy = TaskCapacityPolicy(owner_active_limit=1, global_active_limit=10)

        def create(number: int):
            return repository.create_or_replay(
                pending(number),
                capacity=policy,
            ).disposition

        with ThreadPoolExecutor(max_workers=2) as pool:
            dispositions = tuple(pool.map(create, (10, 11)))

        assert sorted(value.value for value in dispositions) == [
            "created",
            "owner_capacity_exceeded",
        ]


def test_postgres_expired_terminal_rows_are_hidden_in_a_bounded_batch() -> None:
    with migrated_repository() as repository:
        created = repository.create_or_replay(
            pending(20), capacity=TaskCapacityPolicy()
        ).task
        assert created is not None
        claimed = repository.claim_next(worker_id="worker-1", now=NOW + timedelta(seconds=1))
        assert claimed is not None
        assert repository.fail(
            task_id=created.task_id,
            worker_id="worker-1",
            reason="worker_execution_failed",
        )

        run_ids = repository.delete_expired_terminal(
            before=datetime.now(timezone.utc) + timedelta(days=1),
            limit=1,
        )

        assert run_ids == (created.run_id,)
        assert repository.get_by_task_id(owner_id="owner-1", task_id=created.task_id) is None
