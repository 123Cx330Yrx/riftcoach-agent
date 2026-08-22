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
from psycopg.types.json import Jsonb
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_event_record import ReviewTaskEventRecord
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.task_repository import PostgresTaskRepository
from app.persistence.task_repository import _checkpoint_from_storage
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.tasks.models import (
    PendingReviewTask,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.ports import TaskRepositoryError
from app.tasks.reliable_runtime import (
    TaskCancelDisposition,
    TaskCheckpointPhase,
    TaskHeartbeatDisposition,
    TaskLifecycleEventKind,
    project_task_lifecycle,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2026, 8, 22, 14, 0, tzinfo=timezone.utc)
TOKEN_1 = "1" * 64
TOKEN_2 = "2" * 64


def pending(number: int, *, owner_id: str = "owner-reliable") -> PendingReviewTask:
    return PendingReviewTask(
        task_id=UUID(f"82000000-0000-4000-8000-{number:012d}"),
        run_id=f"review_reliable_repository_{number}",
        owner_id=owner_id,
        idempotency_key=f"reliable-request-{number}",
        request_fingerprint=f"{number:064x}",
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        created_at=BASE + timedelta(seconds=number),
    )


def terminal(run_id: str) -> TaskTerminal:
    return TaskTerminal(
        run_id=run_id,
        terminal_reason="quality_gate_passed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        trace_reference=RuntimeTraceReference(run_id=run_id, sha256="a" * 64),
        receipt_reference=RunReceiptReference(run_id=run_id, sha256="b" * 64),
        artifact_reference=RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="c" * 64,
            producer="review_harness.publisher",
        ),
    )


@contextmanager
def migrated_repository() -> Iterator[
    tuple[PostgresTaskRepository, sessionmaker[Session]]
]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL evidence runs in CI"
        )
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = build_engine(DatabaseSettings(url=url))
    factory = build_session_factory(engine)
    tokens = iter((TOKEN_1, TOKEN_2, "3" * 64, "4" * 64))
    try:
        yield PostgresTaskRepository(
            factory,
            lease_token_factory=lambda: next(tokens),
        ), factory
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def create(repository: PostgresTaskRepository, task: PendingReviewTask) -> None:
    result = repository.create_or_replay(
        task,
        capacity=TaskCapacityPolicy(owner_active_limit=10, global_active_limit=100),
    )
    assert result.task is not None


def test_repository_exposes_reliable_control_plane_without_opening_database() -> None:
    repository = PostgresTaskRepository(
        lambda: None,  # type: ignore[arg-type]
        lease_token_factory=lambda: TOKEN_1,
    )

    for method_name in (
        "heartbeat",
        "save_checkpoint",
        "request_cancel",
        "cancel_running",
        "read_events",
    ):
        assert callable(getattr(repository, method_name))


def test_checkpoint_json_storage_round_trips_through_strict_contract() -> None:
    stored = {
            "schema_version": "1.0",
            "checkpoint_id": "claimed-1-1",
            "run_id": "review_reliable_repository_1",
            "checkpoint_sequence": 1,
            "lease_generation": 1,
            "phase": "claimed_safe",
            "safe_to_replay": True,
            "created_at": "2026-08-22T15:00:00Z",
        }
    checkpoint = _checkpoint_from_storage(stored)
    wrapped = _checkpoint_from_storage(Jsonb(stored))
    assert checkpoint.phase is TaskCheckpointPhase.CLAIMED_SAFE
    assert checkpoint.created_at == BASE.replace(hour=15)
    assert wrapped == checkpoint


def test_create_queued_task_persists_sql_null_checkpoint() -> None:
    with migrated_repository() as (repository, factory):
        task = pending(1)
        create(repository, task)

        with factory() as session:
            checkpoint_is_sql_null = session.scalar(
                sa.select(
                    ReviewTaskRecord.checkpoint_reference.is_(None)
                ).where(ReviewTaskRecord.task_id == task.task_id)
            )

        assert checkpoint_is_sql_null is True


def test_create_replay_and_claim_append_one_contiguous_history() -> None:
    with migrated_repository() as (repository, factory):
        task = pending(1)
        create(repository, task)
        repository.create_or_replay(task, capacity=TaskCapacityPolicy())

        claimed = repository.claim_next(
            worker_id="worker-reliable-1",
            now=BASE + timedelta(minutes=1),
            lease_seconds=120,
        )
        assert claimed is not None
        assert claimed.lease is not None
        assert claimed.lease.generation == 1
        assert claimed.lease.private_token == TOKEN_1
        assert claimed.checkpoint_reference is not None
        assert claimed.checkpoint_reference.phase is TaskCheckpointPhase.CLAIMED_SAFE

        page = repository.read_events(
            owner_id=task.owner_id,
            task_id=task.task_id,
            after_cursor=0,
            limit=10,
        )
        assert tuple(item.event_kind for item in page.events) == (
            TaskLifecycleEventKind.CREATED,
            TaskLifecycleEventKind.CLAIMED,
            TaskLifecycleEventKind.CHECKPOINTED,
        )
        assert project_task_lifecycle(page.events).status is TaskStatus.RUNNING
        assert page.has_more is False
        assert page.next_cursor == page.events[-1].event_cursor

        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ReviewTaskEventRecord)
            ) == 3


def test_heartbeat_checkpoint_and_terminal_require_live_fencing_identity() -> None:
    with migrated_repository() as (repository, _factory):
        task = pending(1)
        create(repository, task)
        claimed = repository.claim_next(
            worker_id="worker-reliable-1",
            now=BASE + timedelta(minutes=1),
            lease_seconds=120,
        )
        assert claimed is not None and claimed.lease is not None
        lease = claimed.lease

        lost = repository.heartbeat(
            task_id=task.task_id,
            worker_id=lease.worker_id,
            lease_generation=lease.generation,
            lease_token="f" * 64,
            now=BASE + timedelta(minutes=1, seconds=20),
            lease_seconds=120,
        )
        assert lost.disposition is TaskHeartbeatDisposition.LOST

        active = repository.heartbeat(
            task_id=task.task_id,
            worker_id=lease.worker_id,
            lease_generation=lease.generation,
            lease_token=lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=20),
            lease_seconds=120,
        )
        assert active.disposition is TaskHeartbeatDisposition.ACTIVE
        assert active.lease_expires_at == BASE + timedelta(minutes=3, seconds=20)

        assert repository.save_checkpoint(
            task_id=task.task_id,
            worker_id=lease.worker_id,
            lease_generation=lease.generation,
            lease_token=lease.private_token,
            checkpoint_id="execution-started-1",
            phase=TaskCheckpointPhase.EXECUTION_STARTED,
            now=BASE + timedelta(minutes=1, seconds=21),
        )
        assert not repository.succeed(
            task_id=task.task_id,
            worker_id=lease.worker_id,
            lease_generation=lease.generation,
            lease_token="f" * 64,
            now=BASE + timedelta(minutes=1, seconds=30),
            terminal=terminal(task.run_id),
        )
        assert repository.succeed(
            task_id=task.task_id,
            worker_id=lease.worker_id,
            lease_generation=lease.generation,
            lease_token=lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=30),
            terminal=terminal(task.run_id),
        )
        assert not repository.succeed(
            task_id=task.task_id,
            worker_id=lease.worker_id,
            lease_generation=lease.generation,
            lease_token=lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=31),
            terminal=terminal(task.run_id),
        )


def test_expired_lease_rejects_late_terminal() -> None:
    with migrated_repository() as (repository, _factory):
        task = pending(1)
        create(repository, task)
        claimed = repository.claim_next(
            worker_id="worker-reliable-1",
            now=BASE + timedelta(minutes=1),
            lease_seconds=30,
        )
        assert claimed is not None and claimed.lease is not None

        assert not repository.fail(
            task_id=task.task_id,
            worker_id=claimed.lease.worker_id,
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=31),
            reason="worker_execution_failed",
        )


def test_cancel_is_owner_scoped_idempotent_and_blocks_success() -> None:
    with migrated_repository() as (repository, _factory):
        queued = pending(1)
        running = pending(2)
        create(repository, queued)
        create(repository, running)

        assert repository.request_cancel(
            owner_id="other-owner",
            task_id=queued.task_id,
            request_id="cancel-queued-1",
            reason="user_requested",
            now=BASE + timedelta(minutes=1),
        ) is None
        cancelled = repository.request_cancel(
            owner_id=queued.owner_id,
            task_id=queued.task_id,
            request_id="cancel-queued-1",
            reason="user_requested",
            now=BASE + timedelta(minutes=1),
        )
        assert cancelled is not None
        assert cancelled.disposition is TaskCancelDisposition.CANCELLED

        claimed = repository.claim_next(
            worker_id="worker-reliable-1",
            now=BASE + timedelta(minutes=2),
            lease_seconds=120,
        )
        assert claimed is not None and claimed.task_id == running.task_id
        assert claimed.lease is not None
        requested = repository.request_cancel(
            owner_id=running.owner_id,
            task_id=running.task_id,
            request_id="cancel-running-1",
            reason="user_requested",
            now=BASE + timedelta(minutes=2, seconds=10),
        )
        replayed = repository.request_cancel(
            owner_id=running.owner_id,
            task_id=running.task_id,
            request_id="cancel-running-1",
            reason="user_requested",
            now=BASE + timedelta(minutes=2, seconds=11),
        )
        assert requested is not None and replayed is not None
        assert requested.disposition is TaskCancelDisposition.REQUESTED
        assert replayed.disposition is TaskCancelDisposition.ALREADY_REQUESTED
        assert not repository.succeed(
            task_id=running.task_id,
            worker_id=claimed.lease.worker_id,
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=2, seconds=20),
            terminal=terminal(running.run_id),
        )
        assert repository.cancel_running(
            task_id=running.task_id,
            worker_id=claimed.lease.worker_id,
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=2, seconds=20),
        )


def test_event_replay_is_owner_scoped_cursor_bounded_and_body_free() -> None:
    with migrated_repository() as (repository, _factory):
        task = pending(1)
        create(repository, task)
        claimed = repository.claim_next(
            worker_id="worker-reliable-1",
            now=BASE + timedelta(minutes=1),
            lease_seconds=120,
        )
        assert claimed is not None

        assert repository.read_events(
            owner_id="other-owner",
            task_id=task.task_id,
            after_cursor=0,
            limit=2,
        ) is None
        first = repository.read_events(
            owner_id=task.owner_id,
            task_id=task.task_id,
            after_cursor=0,
            limit=2,
        )
        assert first is not None
        assert len(first.events) == 2
        assert first.has_more is True
        second = repository.read_events(
            owner_id=task.owner_id,
            task_id=task.task_id,
            after_cursor=first.next_cursor,
            limit=2,
        )
        assert second is not None and len(second.events) == 1
        serialized = str(
            [item.model_dump(mode="json") for item in first.events + second.events]
        ).lower()
        assert "riot_id" not in serialized
        assert "prompt" not in serialized
        assert TOKEN_1 not in serialized


def test_operation_identity_collision_rolls_back_cancel_mutation() -> None:
    with migrated_repository() as (repository, _factory):
        task = pending(1)
        create(repository, task)

        with pytest.raises(TaskRepositoryError):
            repository.request_cancel(
                owner_id=task.owner_id,
                task_id=task.task_id,
                request_id="created",
                reason="user_requested",
                now=BASE + timedelta(minutes=1),
            )

        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        page = repository.read_events(
            owner_id=task.owner_id,
            task_id=task.task_id,
            after_cursor=0,
            limit=10,
        )
        assert stored is not None and stored.status is TaskStatus.QUEUED
        assert page is not None and len(page.events) == 1


def test_cancel_and_success_are_linearized_by_one_task_row() -> None:
    with migrated_repository() as (repository, _factory):
        task = pending(1)
        create(repository, task)
        claimed = repository.claim_next(
            worker_id="worker-reliable-1",
            now=BASE + timedelta(minutes=1),
            lease_seconds=120,
        )
        assert claimed is not None and claimed.lease is not None
        barrier = Barrier(2)

        def cancel():
            barrier.wait()
            return repository.request_cancel(
                owner_id=task.owner_id,
                task_id=task.task_id,
                request_id="cancel-race-1",
                reason="user_requested",
                now=BASE + timedelta(minutes=1, seconds=10),
            )

        def succeed():
            barrier.wait()
            return repository.succeed(
                task_id=task.task_id,
                worker_id=claimed.lease.worker_id,
                lease_generation=claimed.lease.generation,
                lease_token=claimed.lease.private_token,
                now=BASE + timedelta(minutes=1, seconds=10),
                terminal=terminal(task.run_id),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            cancel_result = pool.submit(cancel)
            success_result = pool.submit(succeed)
            cancelled = cancel_result.result(timeout=10)
            succeeded = success_result.result(timeout=10)

        assert cancelled is not None
        assert (succeeded, cancelled.disposition) in {
            (True, TaskCancelDisposition.ALREADY_TERMINAL),
            (False, TaskCancelDisposition.REQUESTED),
        }


def test_cancelled_terminal_is_included_in_bounded_retention_cleanup() -> None:
    with migrated_repository() as (repository, _factory):
        task = pending(1)
        create(repository, task)
        cancelled = repository.request_cancel(
            owner_id=task.owner_id,
            task_id=task.task_id,
            request_id="cancel-cleanup-1",
            reason="user_requested",
            now=BASE + timedelta(minutes=1),
        )
        assert cancelled is not None

        assert repository.delete_expired_terminal(
            before=BASE + timedelta(days=1),
            limit=1,
        ) == (task.run_id,)
