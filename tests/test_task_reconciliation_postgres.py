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
from app.persistence.evidence_snapshot_record import EvidenceBundleSnapshotRecord
from app.persistence.task_event_record import ReviewTaskEventRecord
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
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reliable_runtime import TaskCheckpointPhase, TaskLifecycleEventKind
from app.tasks.reconciliation import (
    ExpiredReviewTaskRecovery,
    TaskReconciliationError,
    ManualRecoveryStatus,
    ManualReviewTaskRecovery,
    RecentReviewTerminalEvidenceVerifier,
    ReconciliationStatus,
    ReviewTaskReconciler,
)
from app.persistence.task_record import ReviewTaskRecord
from tests.test_run_query_service import _create_terminal_run
from tests.test_evidence_publication_store import prepared
from tests.test_evidence_task_recovery import bound_task, publication_context


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


def ready_task(repository, tmp_path, *, rejected=False):
    source = bound_task()
    pending = PendingReviewTask(
        task_id=source.task_id, run_id=source.run_id, owner_id=source.owner_id,
        idempotency_key=source.idempotency_key,
        publication_mode=source.publication_mode,
        request_payload=source.request_payload,
        request_fingerprint=source.request_fingerprint,
        created_at=source.created_at,
    )
    claimed = create_and_claim(repository, pending)
    assert repository.save_checkpoint(
        task_id=claimed.task_id, worker_id=claimed.worker_id,
        lease_generation=claimed.lease.generation,
        lease_token=claimed.lease.private_token,
        checkpoint_id="execution-started-1", phase=TaskCheckpointPhase.EXECUTION_STARTED,
        now=claimed.claimed_at + timedelta(seconds=1),
    )
    claimed = repository.get_by_task_id(owner_id=claimed.owner_id, task_id=claimed.task_id)
    app, deps, store, _ = prepared(tmp_path, rejected=rejected)
    terminal = RecentReviewTaskExecutor(
        application_service=app,
        evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        runs_root=tmp_path,
    ).execute(claimed)
    # Simulate the crash after durable files and before the worker's SQL commit.
    return claimed, deps, store, terminal


def recover(repository, task, tmp_path, path="single"):
    verifier = RecentReviewTerminalEvidenceVerifier(tmp_path)
    if path == "single":
        return ReviewTaskReconciler(repository=repository, verifier=verifier).reconcile(
            task, now=task.lease.expires_at,
        )
    return ExpiredReviewTaskRecovery(repository=repository, verifier=verifier).recover_batch(
        now=task.lease.expires_at,
    )[0]


def assert_unpublished(factory, task):
    with factory() as session:
        row = session.get(ReviewTaskRecord, task.task_id)
        assert row.status == TaskStatus.RUNNING.value
        assert row.publication_reference is None and row.summary_digest is None
        assert row.first_snapshot_id is None and row.first_snapshot_digest is None
        assert session.scalar(sa.select(sa.func.count()).select_from(
            EvidenceBundleSnapshotRecord)) == 0
        assert session.scalar(sa.select(sa.func.count()).select_from(
            ReviewTaskEventRecord).where(
                ReviewTaskEventRecord.event_kind == TaskLifecycleEventKind.RECONCILED.value,
            )) == 0


@pytest.mark.parametrize("path", ["single", "batch"])
@pytest.mark.parametrize("rejected", [False, True])
def test_real_file_recovery_commits_one_snapshot_terminal_and_event(tmp_path, path, rejected):
    with migrated_repository() as (repository, factory):
        task, deps, store, terminal = ready_task(repository, tmp_path, rejected=rejected)
        calls = tuple(deps["provider"].requests)
        assert_unpublished(factory, task)
        assert recover(repository, task, tmp_path, path).status.value == "reconciled"
        manifest = store.read(publication_context(task))
        with factory() as session:
            row = session.get(ReviewTaskRecord, task.task_id)
            snapshots = session.scalars(sa.select(EvidenceBundleSnapshotRecord)).all()
            events = session.scalars(sa.select(ReviewTaskEventRecord).where(
                ReviewTaskEventRecord.event_kind == TaskLifecycleEventKind.RECONCILED.value,
            )).all()
            assert row.status == TaskStatus.SUCCEEDED.value
            assert row.publication_status == ("rejected" if rejected else "published")
            assert row.report_available is not rejected
            assert row.summary_digest == manifest.summary_digest
            assert row.publication_reference == terminal.publication_reference
            assert len(snapshots) == len(events) == 1
            snapshot = snapshots[0]
            assert (snapshot.task_id, snapshot.owner_id, snapshot.run_id) == (
                task.task_id, task.owner_id, task.run_id,
            )
            assert row.first_snapshot_id == snapshot.snapshot_id
            assert row.first_snapshot_digest == snapshot.snapshot_digest
            assert snapshot.bundle_digest == manifest.bundle.bundle_digest
        # The same expired generation cannot publish a second snapshot/event.
        assert recover(repository, task, tmp_path).status.value == "ownership_lost"
        with factory() as session:
            assert session.scalar(sa.select(sa.func.count()).select_from(
                EvidenceBundleSnapshotRecord)) == 1
            assert session.scalar(sa.select(sa.func.count()).select_from(
                ReviewTaskEventRecord).where(
                    ReviewTaskEventRecord.event_kind == TaskLifecycleEventKind.RECONCILED.value,
                )) == 1
        assert tuple(deps["provider"].requests) == calls


def test_recovery_event_failure_rolls_back_snapshot_and_terminal(tmp_path, monkeypatch):
    with migrated_repository() as (repository, factory):
        task, deps, _, _ = ready_task(repository, tmp_path)
        calls = tuple(deps["provider"].requests)
        original = repository._append_event
        def fail_event(*args, **kwargs):
            if kwargs["event_kind"] is TaskLifecycleEventKind.RECONCILED:
                raise RuntimeError("injected event transaction failure")
            return original(*args, **kwargs)
        monkeypatch.setattr(repository, "_append_event", fail_event)
        with pytest.raises(TaskReconciliationError, match="task_terminal_update_failed"):
            recover(repository, task, tmp_path)
        assert_unpublished(factory, task)
        monkeypatch.setattr(repository, "_append_event", original)
        assert recover(repository, task, tmp_path).status.value == "reconciled"
        assert tuple(deps["provider"].requests) == calls


@pytest.mark.parametrize("fence", ["lease_token", "cancel"])
def test_expired_recovery_fences_stale_owner_and_cancellation(tmp_path, fence):
    with migrated_repository() as (repository, factory):
        task, _, _, _ = ready_task(repository, tmp_path)
        if fence == "lease_token":
            task = task.model_copy(update={
                "lease": task.lease.model_copy(update={"token": "0" * 64}),
            })
        else:
            repository.request_cancel(
                owner_id=task.owner_id, task_id=task.task_id,
                request_id="cancel-before-recovery", reason="user_requested",
                now=task.lease.expires_at,
            )
        assert recover(repository, task, tmp_path).status.value == "ownership_lost"
        assert_unpublished(factory, task)


def test_tampered_evidence_does_not_create_a_partial_database_publication(tmp_path):
    with migrated_repository() as (repository, factory):
        task, _, store, _ = ready_task(repository, tmp_path)
        (tmp_path / task.run_id / store.filename).write_bytes(b"tampered")
        assert recover(repository, task, tmp_path).status.value == "recovery_required"
        assert_unpublished(factory, task)
