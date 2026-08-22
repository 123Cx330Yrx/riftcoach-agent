from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from typing import TypeVar
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.task_repository import PostgresTaskRepository
from app.tasks.models import (
    PendingReviewTask,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
T = TypeVar("T")


@contextmanager
def migrated_repository() -> Iterator[
    tuple[PostgresTaskRepository, sessionmaker[Session]]
]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL claim evidence runs in CI"
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


def pending(number: int, *, created_offset: int | None = None) -> PendingReviewTask:
    return PendingReviewTask(
        task_id=UUID(f"40000000-0000-4000-8000-{number:012d}"),
        run_id=f"review_claim_{number}",
        owner_id=f"owner-{number}",
        idempotency_key=f"request-{number}",
        request_fingerprint=f"{number:064x}",
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        created_at=BASE + timedelta(seconds=created_offset or number),
    )


def create_tasks(
    repository: PostgresTaskRepository,
    *tasks: PendingReviewTask,
) -> None:
    for task in tasks:
        repository.create_or_replay(
            task,
            capacity=TaskCapacityPolicy(
                owner_active_limit=10,
                global_active_limit=100,
            ),
        )


def successful_terminal(
    *,
    run_id: str = "review_claim_1",
) -> TaskTerminal:
    return TaskTerminal(
        run_id=run_id,
        terminal_reason="quality_gate_passed",
        publication_status=TaskPublicationStatus.PUBLISHED,
        report_available=True,
        trace_reference=RuntimeTraceReference(
            run_id=run_id,
            sha256="a" * 64,
        ),
        receipt_reference=RunReceiptReference(
            run_id=run_id,
            sha256="b" * 64,
        ),
        artifact_reference=RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="c" * 64,
            producer="review_harness.publisher",
        ),
    )


def _result_with_timeout(future: Future[T]) -> T:
    try:
        return future.result(timeout=5)
    except TimeoutError:
        pytest.fail("concurrent PostgreSQL claim timed out or deadlocked")


def test_claim_uses_deterministic_created_at_then_task_id_order() -> None:
    with migrated_repository() as (repository, factory):
        same_time_high_id = pending(3, created_offset=1)
        first = pending(1, created_offset=1)
        later = pending(2, created_offset=2)
        create_tasks(repository, same_time_high_id, later, first)

        claimed = [
            repository.claim_next(
                worker_id=f"worker-{number}",
                now=BASE + timedelta(minutes=number),
            )
            for number in range(1, 4)
        ]

        assert [task.task_id for task in claimed if task is not None] == [
            first.task_id,
            same_time_high_id.task_id,
            later.task_id,
        ]
        assert repository.claim_next(
            worker_id="worker-4",
            now=BASE + timedelta(minutes=4),
        ) is None

        # A claim method must have committed and released its row lock before
        # returning; NOWAIT would fail here if the transaction were still open.
        with factory.begin() as session:
            record = session.scalar(
                sa.select(ReviewTaskRecord)
                .where(ReviewTaskRecord.task_id == first.task_id)
                .with_for_update(nowait=True)
            )
            assert record is not None
            assert record.status == TaskStatus.RUNNING.value


def test_skip_locked_claims_second_row_without_waiting_for_locked_first_row() -> None:
    with migrated_repository() as (repository, factory):
        first = pending(1)
        second = pending(2)
        create_tasks(repository, first, second)

        with factory() as blocker:
            transaction = blocker.begin()
            locked = blocker.scalar(
                sa.select(ReviewTaskRecord)
                .where(ReviewTaskRecord.status == TaskStatus.QUEUED.value)
                .order_by(
                    ReviewTaskRecord.created_at.asc(),
                    ReviewTaskRecord.task_id.asc(),
                )
                .limit(1)
                .with_for_update()
            )
            assert locked is not None
            assert locked.task_id == first.task_id

            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                repository.claim_next,
                worker_id="worker-2",
                now=BASE + timedelta(minutes=1),
            )
            try:
                claimed = _result_with_timeout(future)
            finally:
                # Release the deliberately held row even when the assertion
                # times out, so a broken implementation cannot hang pytest.
                transaction.rollback()
                executor.shutdown(wait=True, cancel_futures=True)

            assert claimed is not None
            assert claimed.task_id == second.task_id

        remaining = repository.claim_next(
            worker_id="worker-1",
            now=BASE + timedelta(minutes=2),
        )
        assert remaining is not None
        assert remaining.task_id == first.task_id


def test_two_workers_concurrently_claim_one_task_at_most_once() -> None:
    with migrated_repository() as (repository, factory):
        task = pending(1)
        create_tasks(repository, task)
        barrier = Barrier(2)

        def claim(worker_id: str):
            barrier.wait(timeout=5)
            return repository.claim_next(
                worker_id=worker_id,
                now=BASE + timedelta(minutes=1),
            )

        executor = ThreadPoolExecutor(max_workers=2)
        futures = [
            executor.submit(claim, worker_id)
            for worker_id in ("worker-1", "worker-2")
        ]
        try:
            results = [_result_with_timeout(future) for future in futures]
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        claimed = [result for result in results if result is not None]
        assert len(claimed) == 1
        assert claimed[0].task_id == task.task_id
        assert claimed[0].worker_id in {"worker-1", "worker-2"}

        with factory() as session:
            records = tuple(session.scalars(sa.select(ReviewTaskRecord)))
            assert len(records) == 1
            assert records[0].status == TaskStatus.RUNNING.value
            assert records[0].worker_id == claimed[0].worker_id


def test_two_workers_concurrently_drain_many_tasks_without_duplicates() -> None:
    with migrated_repository() as (repository, factory):
        tasks = tuple(pending(number) for number in range(1, 7))
        create_tasks(repository, *tasks)
        barrier = Barrier(2)

        def drain(worker_id: str) -> tuple[UUID, ...]:
            barrier.wait(timeout=5)
            claimed_ids: list[UUID] = []
            while True:
                task = repository.claim_next(
                    worker_id=worker_id,
                    now=BASE + timedelta(minutes=1),
                )
                if task is None:
                    return tuple(claimed_ids)
                assert task.worker_id == worker_id
                claimed_ids.append(task.task_id)

        executor = ThreadPoolExecutor(max_workers=2)
        futures = [
            executor.submit(drain, worker_id)
            for worker_id in ("worker-1", "worker-2")
        ]
        try:
            claims_by_worker = [
                _result_with_timeout(future) for future in futures
            ]
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        all_claims = [
            task_id
            for worker_claims in claims_by_worker
            for task_id in worker_claims
        ]
        assert len(all_claims) == len(tasks)
        assert len(set(all_claims)) == len(tasks)
        assert set(all_claims) == {task.task_id for task in tasks}

        with factory() as session:
            records = tuple(
                session.scalars(
                    sa.select(ReviewTaskRecord).order_by(
                        ReviewTaskRecord.created_at.asc(),
                        ReviewTaskRecord.task_id.asc(),
                    )
                )
            )
            assert {record.status for record in records} == {
                TaskStatus.RUNNING.value
            }
            assert {record.worker_id for record in records} <= {
                "worker-1",
                "worker-2",
            }


def test_terminal_success_cas_rejects_wrong_or_stale_worker_without_mutation() -> None:
    with migrated_repository() as (repository, factory):
        task = pending(1)
        create_tasks(repository, task)
        claimed = repository.claim_next(
            worker_id="worker-1",
            now=BASE + timedelta(minutes=1),
        )
        assert claimed is not None and claimed.lease is not None

        assert not repository.succeed(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=1),
            terminal=successful_terminal(run_id="review_other_run"),
        )
        assert not repository.succeed(
            task_id=task.task_id,
            worker_id="worker-2",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=1),
            terminal=successful_terminal(),
        )
        assert not repository.fail(
            task_id=task.task_id,
            worker_id="worker-2",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=1),
            reason="worker_execution_failed",
        )
        running = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert running is not None
        assert running.status is TaskStatus.RUNNING

        assert repository.succeed(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=2),
            terminal=successful_terminal(),
        )
        assert not repository.succeed(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=3),
            terminal=successful_terminal(),
        )
        assert not repository.fail(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=3),
            reason="worker_execution_failed",
        )

        terminal = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert terminal is not None
        assert terminal.status is TaskStatus.SUCCEEDED
        assert terminal.worker_id == "worker-1"
        assert terminal.terminal_reason == "quality_gate_passed"
        assert terminal.publication_status is TaskPublicationStatus.PUBLISHED
        assert terminal.report_available is True
        assert terminal.trace_reference is not None
        assert terminal.trace_reference.run_id == task.run_id
        assert terminal.receipt_reference is not None
        assert terminal.receipt_reference.run_id == task.run_id
        assert terminal.artifact_reference is not None
        assert terminal.artifact_reference.kind == "final_report"


def test_terminal_failure_cas_is_owner_scoped_and_irreversible() -> None:
    with migrated_repository() as (repository, factory):
        task = pending(1)
        create_tasks(repository, task)
        claimed = repository.claim_next(
            worker_id="worker-1",
            now=BASE + timedelta(minutes=1),
        )
        assert claimed is not None and claimed.lease is not None

        assert repository.fail(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=1),
            reason="worker_execution_failed",
        )
        assert not repository.succeed(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=2),
            terminal=successful_terminal(),
        )

        terminal = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert terminal is not None
        assert terminal.status is TaskStatus.FAILED
        assert terminal.worker_id == "worker-1"
        assert terminal.terminal_reason == "worker_execution_failed"
        assert terminal.publication_status is None
        assert terminal.report_available is False


def test_terminal_timestamp_remains_monotonic_when_worker_clock_is_ahead() -> None:
    with migrated_repository() as (repository, factory):
        task = pending(1)
        create_tasks(repository, task)
        future_claim = datetime.now(timezone.utc) + timedelta(days=1)
        claimed = repository.claim_next(
            worker_id="worker-1",
            now=future_claim,
        )
        assert claimed is not None and claimed.lease is not None

        assert repository.succeed(
            task_id=task.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=future_claim + timedelta(seconds=1),
            terminal=successful_terminal(),
        )
        terminal = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert terminal is not None
        assert terminal.claimed_at == future_claim
        assert terminal.finished_at is not None
        assert terminal.finished_at >= terminal.claimed_at
        assert terminal.updated_at >= terminal.claimed_at
