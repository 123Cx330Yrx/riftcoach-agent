from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_repository import PostgresTaskRepository
from app.product.run_receipts import RunReceiptReference
from app.runtime.models import RuntimeArtifactReference, RuntimeTraceReference
from app.tasks.fingerprint import compute_task_request_fingerprint
from app.tasks.models import (
    PendingReviewTask,
    ReviewTask,
    TaskCapacityPolicy,
    TaskPublicationStatus,
    TaskStatus,
    TaskTerminal,
)
from app.tasks.reconciliation import (
    ManualRecoveryStatus,
    ManualReviewTaskRecovery,
    RecentReviewTerminalEvidenceVerifier,
    ReconciliationStatus,
    ReviewTaskReconciler,
)
from app.persistence.task_record import ReviewTaskRecord
from tests.test_run_query_service import _create_terminal_run


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2026, 8, 18, 7, 0, tzinfo=timezone.utc)


@contextmanager
def migrated_repository() -> Iterator[
    tuple[PostgresTaskRepository, sessionmaker[Session]]
]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; reconciliation evidence runs in CI"
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


def pending(number: int, *, run_id: str | None = None) -> PendingReviewTask:
    payload = {
        "riot_id": "DemoPlayer#TEST",
        "count": 10,
        "queue": 420,
        "focus": "overall",
    }
    return PendingReviewTask(
        task_id=UUID(f"60000000-0000-4000-8000-{number:012d}"),
        run_id=run_id or f"review_reconcile_{number}",
        owner_id="owner-1",
        idempotency_key=f"request-{number}",
        request_fingerprint=compute_task_request_fingerprint(
            task_kind="recent_review",
            schema_version="1.0",
            request_payload=payload,
        ),
        request_payload=payload,
        created_at=BASE + timedelta(seconds=number),
    )


def create_and_claim(
    repository: PostgresTaskRepository,
    task: PendingReviewTask,
    *,
    worker_id: str = "worker-1",
) -> ReviewTask:
    created = repository.create_or_replay(
        task,
        capacity=TaskCapacityPolicy(owner_active_limit=10, global_active_limit=20),
    )
    assert created.task is not None
    claimed = repository.claim_next(
        worker_id=worker_id,
        now=task.created_at + timedelta(minutes=1),
    )
    assert claimed is not None
    assert claimed.task_id == task.task_id
    return claimed


def test_complete_receipt_reconciles_running_task_to_succeeded(tmp_path: Path):
    with migrated_repository() as (repository, _factory):
        task = pending(1, run_id="review_reconcile_complete")
        claimed = create_and_claim(repository, task)
        _create_terminal_run(tmp_path, run_id=task.run_id)

        result = ReviewTaskReconciler(
            repository=repository,
            verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        ).reconcile(claimed, now=claimed.lease.expires_at)

        assert result.status is ReconciliationStatus.RECONCILED
        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert stored is not None
        assert stored.status is TaskStatus.SUCCEEDED
        assert stored.run_id == task.run_id
        assert stored.receipt_reference is not None
        assert stored.trace_reference is not None
        assert stored.artifact_reference is not None


def test_missing_receipt_is_recovery_required_and_not_automatically_failed(
    tmp_path: Path,
):
    with migrated_repository() as (repository, _factory):
        task = pending(2, run_id="review_reconcile_missing")
        claimed = create_and_claim(repository, task)

        result = ReviewTaskReconciler(
            repository=repository,
            verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        ).reconcile(claimed, now=claimed.lease.expires_at)

        assert result.status is ReconciliationStatus.RECOVERY_REQUIRED
        assert result.reason == "receipt_missing"
        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert stored is not None
        assert stored.status is TaskStatus.RUNNING


def test_manual_recovery_cas_blocks_late_worker_terminal_update():
    with migrated_repository() as (repository, _factory):
        task = pending(3, run_id="review_reconcile_manual")
        claimed = create_and_claim(repository, task)
        assert claimed.lease is not None
        assert repository.mark_recovery_required(
            task_id=claimed.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=claimed.lease.expires_at,
            reason="unsafe_checkpoint",
        )
        recovery = ManualReviewTaskRecovery(
            repository,
            clock=lambda: claimed.lease.expires_at + timedelta(seconds=1),
        )

        result = recovery.recover(
            task_id=claimed.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            confirmation_worker_id="worker-1",
        )
        assert result.status is ManualRecoveryStatus.RECOVERED

        late_terminal = TaskTerminal(
            run_id=task.run_id,
            terminal_reason="quality_gate_passed",
            publication_status=TaskPublicationStatus.PUBLISHED,
            report_available=True,
            trace_reference=RuntimeTraceReference(
                run_id=task.run_id,
                sha256="a" * 64,
            ),
            receipt_reference=RunReceiptReference(
                run_id=task.run_id,
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
        assert not repository.succeed(
            task_id=claimed.task_id,
            worker_id="worker-1",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=claimed.lease.expires_at + timedelta(seconds=2),
            terminal=late_terminal,
        )
        stored = repository.get_by_task_id(
            owner_id=task.owner_id,
            task_id=task.task_id,
        )
        assert stored is not None
        assert stored.status is TaskStatus.FAILED
        assert stored.terminal_reason == "worker_confirmed_dead"


def test_reconciliation_does_not_change_a_task_without_valid_evidence(
    tmp_path: Path,
):
    with migrated_repository() as (repository, _factory):
        task = pending(4, run_id="review_reconcile_stale")
        claimed = create_and_claim(repository, task)
        # The task has no matching receipt; the important property is that a
        # stale running projection remains non-terminal until a valid CAS.
        result = ReviewTaskReconciler(
            repository=repository,
            verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        ).reconcile(claimed, now=claimed.lease.expires_at)
        assert result.status is ReconciliationStatus.RECOVERY_REQUIRED
