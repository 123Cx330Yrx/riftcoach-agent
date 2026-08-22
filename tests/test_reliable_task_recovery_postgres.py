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
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_repository import PostgresTaskRepository
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.tasks.models import (
    PendingReviewTask,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.reconciliation import (
    ExpiredReviewTaskRecovery,
    ManualRecoveryStatus,
    ManualReviewTaskRecovery,
    RecentReviewTerminalEvidenceVerifier,
    TaskRecoveryStatus,
    TaskTerminalEvidenceError,
)
from app.tasks.reliable_runtime import (
    TaskCheckpointPhase,
    TaskLeasePolicy,
    TaskLifecycleEventKind,
)
from tests.test_run_query_service import _create_terminal_run


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2026, 8, 22, 17, 0, tzinfo=timezone.utc)
TOKEN_1 = "1" * 64
TOKEN_2 = "2" * 64


@contextmanager
def migrated_repository() -> Iterator[PostgresTaskRepository]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; recovery evidence runs in CI"
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
    factory: sessionmaker[Session] = build_session_factory(engine)
    tokens = iter((TOKEN_1, TOKEN_2, "3" * 64, "4" * 64))
    try:
        yield PostgresTaskRepository(
            factory,
            lease_token_factory=lambda: next(tokens),
        )
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def pending(number: int, *, run_id: str | None = None) -> PendingReviewTask:
    return PendingReviewTask(
        task_id=UUID(f"84000000-0000-4000-8000-{number:012d}"),
        run_id=run_id or f"review_recovery_postgres_{number}",
        owner_id="owner-recovery",
        idempotency_key=f"recovery-request-{number}",
        request_fingerprint=f"{number:064x}",
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "overall",
        },
        created_at=BASE + timedelta(seconds=number),
    )


def create_and_claim(repository: PostgresTaskRepository, task: PendingReviewTask):
    created = repository.create_or_replay(
        task,
        capacity=TaskCapacityPolicy(owner_active_limit=10, global_active_limit=20),
    )
    assert created.task is not None
    claimed = repository.claim_next(
        worker_id="worker-recovery-1",
        now=BASE + timedelta(minutes=1),
        lease_seconds=30,
    )
    assert claimed is not None and claimed.lease is not None
    return claimed


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


class MissingReceiptVerifier:
    def terminal_for(self, _task):
        raise TaskTerminalEvidenceError("receipt_missing")


class ExplodingVerifier:
    def terminal_for(self, _task):
        raise AssertionError("cancel recovery must not read receipt evidence")


def recovery(repository, verifier, *, max_recoveries: int = 3):
    return ExpiredReviewTaskRecovery(
        repository=repository,
        verifier=verifier,
        policy=TaskLeasePolicy(max_recoveries=max_recoveries),
    )


def test_expired_cancel_is_terminal_and_fences_late_worker() -> None:
    with migrated_repository() as repository:
        task = pending(1)
        claimed = create_and_claim(repository, task)
        repository.request_cancel(
            owner_id=task.owner_id,
            task_id=task.task_id,
            request_id="cancel-expired-1",
            reason="user_requested",
            now=BASE + timedelta(minutes=1, seconds=10),
        )

        result = recovery(repository, ExplodingVerifier()).recover_batch(
            now=BASE + timedelta(minutes=1, seconds=31)
        )

        assert result[0].status is TaskRecoveryStatus.CANCELLED
        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert stored is not None and stored.status is TaskStatus.CANCELLED
        assert not repository.fail(
            task_id=task.task_id,
            worker_id=claimed.lease.worker_id,
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=32),
            reason="late_worker",
        )


def test_claimed_safe_requeues_and_next_claim_advances_generation() -> None:
    with migrated_repository() as repository:
        task = pending(1)
        claimed = create_and_claim(repository, task)

        result = recovery(repository, MissingReceiptVerifier()).recover_batch(
            now=BASE + timedelta(minutes=1, seconds=31)
        )

        assert result[0].status is TaskRecoveryStatus.REQUEUED
        queued = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert queued is not None
        assert queued.status is TaskStatus.QUEUED
        assert queued.worker_id is None and queued.lease is None
        assert queued.recovery_count == 1
        assert not repository.fail(
            task_id=task.task_id,
            worker_id=claimed.lease.worker_id,
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=BASE + timedelta(minutes=1, seconds=32),
            reason="late_worker",
        )
        claimed_again = repository.claim_next(
            worker_id="worker-recovery-2",
            now=BASE + timedelta(minutes=2),
            lease_seconds=30,
        )
        assert claimed_again is not None and claimed_again.lease is not None
        assert claimed_again.lease.generation == 2
        assert claimed_again.lease.private_token == TOKEN_2


def test_started_execution_requires_manual_generation_matched_failure() -> None:
    with migrated_repository() as repository:
        task = pending(1)
        claimed = create_and_claim(repository, task)
        assert repository.save_checkpoint(
            task_id=task.task_id,
            worker_id=claimed.lease.worker_id,
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            checkpoint_id="execution-started-1",
            phase=TaskCheckpointPhase.EXECUTION_STARTED,
            now=BASE + timedelta(minutes=1, seconds=1),
        )

        result = recovery(repository, MissingReceiptVerifier()).recover_batch(
            now=BASE + timedelta(minutes=1, seconds=31)
        )

        assert result[0].status is TaskRecoveryStatus.RECOVERY_REQUIRED
        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert stored is not None
        assert stored.status is TaskStatus.RECOVERY_REQUIRED
        assert stored.recovery_reason == "unsafe_checkpoint"
        manual = ManualReviewTaskRecovery(
            repository,
            clock=lambda: BASE + timedelta(minutes=2),
        )
        assert manual.recover(
            task_id=task.task_id,
            worker_id="worker-recovery-1",
            lease_generation=2,
            confirmation_worker_id="worker-recovery-1",
        ).status is ManualRecoveryStatus.NOT_RECOVERED
        assert manual.recover(
            task_id=task.task_id,
            worker_id="worker-recovery-1",
            lease_generation=1,
            confirmation_worker_id="worker-recovery-1",
        ).status is ManualRecoveryStatus.RECOVERED


def test_complete_receipt_reconciles_expired_task(tmp_path: Path) -> None:
    with migrated_repository() as repository:
        task = pending(1, run_id="review_recovery_receipt")
        create_and_claim(repository, task)
        _create_terminal_run(tmp_path, run_id=task.run_id)

        result = recovery(
            repository,
            RecentReviewTerminalEvidenceVerifier(tmp_path),
        ).recover_batch(now=BASE + timedelta(minutes=1, seconds=31))

        assert result[0].status is TaskRecoveryStatus.RECONCILED
        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert stored is not None and stored.status is TaskStatus.SUCCEEDED
        page = repository.read_events(
            owner_id=task.owner_id,
            task_id=task.task_id,
            after_cursor=0,
            limit=20,
        )
        assert page is not None
        assert page.events[-1].event_kind is TaskLifecycleEventKind.RECONCILED


def test_recovery_and_live_terminal_cas_allow_exactly_one_winner() -> None:
    with migrated_repository() as repository:
        task = pending(1)
        claimed = create_and_claim(repository, task)
        barrier = Barrier(2)

        def late_terminal() -> bool:
            barrier.wait()
            return repository.succeed(
                task_id=task.task_id,
                worker_id=claimed.lease.worker_id,
                lease_generation=claimed.lease.generation,
                lease_token=claimed.lease.private_token,
                now=BASE + timedelta(minutes=1, seconds=29, microseconds=999999),
                terminal=terminal(task.run_id),
            )

        def expired_recovery() -> bool:
            barrier.wait()
            return repository.mark_recovery_required(
                task_id=task.task_id,
                worker_id=claimed.lease.worker_id,
                lease_generation=claimed.lease.generation,
                lease_token=claimed.lease.private_token,
                now=BASE + timedelta(minutes=1, seconds=30),
                reason="unsafe_checkpoint",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = tuple(
                future.result(timeout=10)
                for future in (
                    pool.submit(late_terminal),
                    pool.submit(expired_recovery),
                )
            )

        assert sum(outcomes) == 1
