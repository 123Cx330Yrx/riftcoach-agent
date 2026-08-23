from __future__ import annotations

import copy
import io
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
from alembic.script import ScriptDirectory
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, sessionmaker

from app.evidence.storage import (
    EvidenceSnapshotWriteDisposition,
    PendingEvidenceBundleSnapshot,
)
from app.evidence.fusion import EvidenceBundleDisposition
from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.evidence_snapshot_record import EvidenceBundleSnapshotRecord
from app.persistence.evidence_snapshot_repository import (
    PostgresEvidenceSnapshotRepository,
)
from app.persistence.task_repository import PostgresTaskRepository
from app.tasks.models import PendingReviewTask, TaskCapacityPolicy
from tests.test_evidence_snapshot_contracts import bundle


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
HEAD = "0011_evidence_product_api"
NOW = datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc)
TASK_ID = UUID("93000000-0000-4000-8000-000000000001")
RUN_ID = "review_evidence_repository_1"


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def test_evidence_snapshot_metadata_and_migration_head_are_explicit() -> None:
    table = EvidenceBundleSnapshotRecord.__table__
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()

    assert head == HEAD
    assert table.name == "evidence_bundle_snapshots"
    assert table.c.payload.type.__class__ is JSONB
    assert table.c.stored_at.type.timezone is True
    assert table.c.expires_at.type.timezone is True
    assert {
        "pk_evidence_bundle_snapshots",
        "uq_evidence_bundle_snapshots_task_revision",
        "uq_evidence_bundle_snapshots_task_refresh",
        "fk_evidence_bundle_snapshots_task_identity",
        "ck_evidence_bundle_snapshots_revision_positive",
        "ck_evidence_bundle_snapshots_bundle_digest_format",
        "ck_evidence_bundle_snapshots_snapshot_digest_format",
        "ck_evidence_bundle_snapshots_payload_bound",
    } <= {constraint.name for constraint in table.constraints}
    assert {
        "ix_evidence_bundle_snapshots_owner_run_revision",
        "ix_evidence_bundle_snapshots_task_revision",
    } <= {index.name for index in table.indexes}


def test_0011_offline_sql_has_append_only_snapshot_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach",
    )
    output = io.StringIO()
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()

    assert "CREATE TABLE evidence_bundle_snapshots" in sql
    assert "fk_evidence_bundle_snapshots_task_identity" in sql
    assert "ON DELETE CASCADE" in sql
    assert "ck_evidence_bundle_snapshots_payload_bound" in sql
    assert "prevent_evidence_bundle_snapshot_update" in sql
    assert "CREATE INDEX ix_evidence_bundle_snapshots_owner_run_revision" in sql


def pending_task() -> PendingReviewTask:
    return PendingReviewTask(
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id="owner-1",
        idempotency_key="evidence-task-1",
        request_fingerprint="9" * 64,
        request_payload={
            "riot_id": "DemoPlayer#TEST",
            "routing_region": "asia",
            "count": 5,
            "queue": 420,
            "focus": "overall",
        },
        created_at=NOW - timedelta(minutes=1),
    )


def pending_snapshot(
    refresh_id: str,
    *,
    evidence=None,
) -> PendingEvidenceBundleSnapshot:
    return PendingEvidenceBundleSnapshot(
        task_id=TASK_ID,
        run_id=RUN_ID,
        owner_id="owner-1",
        refresh_id=refresh_id,
        bundle=evidence or bundle(),
        stored_at=NOW,
    )


@contextmanager
def migrated_repositories() -> Iterator[
    tuple[
        PostgresTaskRepository,
        PostgresEvidenceSnapshotRepository,
        sessionmaker[Session],
    ]
]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL evidence runs in CI"
        )
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = build_engine(DatabaseSettings(url=url))
    factory = build_session_factory(engine)
    try:
        yield (
            PostgresTaskRepository(
                factory,
                lease_token_factory=lambda: "1" * 64,
            ),
            PostgresEvidenceSnapshotRepository(factory),
            factory,
        )
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def create_running_task(repository: PostgresTaskRepository) -> None:
    result = repository.create_or_replay(
        pending_task(),
        capacity=TaskCapacityPolicy(owner_active_limit=5, global_active_limit=20),
    )
    assert result.task is not None
    claimed = repository.claim_next(worker_id="evidence-worker", now=NOW)
    assert claimed is not None and claimed.task_id == TASK_ID


def test_repository_append_replay_refresh_latest_and_owner_scope() -> None:
    with migrated_repositories() as (tasks, evidence, _factory):
        create_running_task(tasks)

        first = evidence.append(pending_snapshot("refresh-1"))
        replay = evidence.append(
            pending_snapshot("refresh-1").model_copy(
                update={"stored_at": NOW + timedelta(seconds=1)}
            )
        )
        second = evidence.append(pending_snapshot("refresh-2"))

        assert first.disposition is EvidenceSnapshotWriteDisposition.CREATED
        assert first.snapshot.revision == 1
        assert replay.disposition is EvidenceSnapshotWriteDisposition.REPLAYED
        assert replay.snapshot == first.snapshot
        assert second.snapshot.revision == 2
        assert evidence.get_latest(owner_id="owner-1", run_id=RUN_ID) == second.snapshot
        assert evidence.get_latest(owner_id="owner-2", run_id=RUN_ID) is None


def test_refresh_identity_conflict_and_storage_tamper_fail_closed() -> None:
    with migrated_repositories() as (tasks, evidence, factory):
        create_running_task(tasks)
        evidence.append(pending_snapshot("refresh-1"))

        with pytest.raises(Exception) as conflict:
            evidence.append(
                pending_snapshot(
                    "refresh-1",
                    evidence=bundle(
                        disposition=EvidenceBundleDisposition.DEGRADED
                    ),
                )
            )
        assert "evidence_snapshot_conflict" in str(conflict.value)

        with factory() as session, session.begin():
            record = session.scalar(sa.select(EvidenceBundleSnapshotRecord))
            assert record is not None
            # The database append-only trigger rejects ordinary UPDATE. Disable it
            # only inside this test transaction to prove read-time digest defense.
            session.execute(
                sa.text(
                    "ALTER TABLE evidence_bundle_snapshots DISABLE TRIGGER "
                    "trg_evidence_bundle_snapshots_no_update"
                )
            )
            # JSONB values are plain nested containers here.  Deep-copy before
            # mutating so SQLAlchemy observes a genuinely new top-level value
            # and emits the intentional tamper UPDATE.
            payload = copy.deepcopy(record.payload)
            payload["riot_matches"][0]["win"] = False
            record.payload = payload
            session.flush()
            session.execute(
                sa.text(
                    "ALTER TABLE evidence_bundle_snapshots ENABLE TRIGGER "
                    "trg_evidence_bundle_snapshots_no_update"
                )
            )

        with pytest.raises(Exception) as integrity:
            evidence.get_latest(owner_id="owner-1", run_id=RUN_ID)
        assert "evidence_snapshot_integrity_failed" in str(integrity.value)


def test_concurrent_refreshes_get_distinct_contiguous_revisions() -> None:
    with migrated_repositories() as (tasks, evidence, _factory):
        create_running_task(tasks)
        barrier = Barrier(2)

        def append(refresh_id: str):
            barrier.wait(timeout=10)
            return evidence.append(pending_snapshot(refresh_id)).snapshot.revision

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (
                pool.submit(append, "refresh-a"),
                pool.submit(append, "refresh-b"),
            )
            revisions = sorted(future.result(timeout=15) for future in futures)

        assert revisions == [1, 2]


def test_task_delete_cascades_snapshots_and_update_trigger_is_active() -> None:
    with migrated_repositories() as (tasks, evidence, factory):
        create_running_task(tasks)
        created = evidence.append(pending_snapshot("refresh-1"))

        with factory() as session:
            with pytest.raises(sa.exc.DBAPIError):
                with session.begin():
                    session.execute(
                        sa.update(EvidenceBundleSnapshotRecord)
                        .where(
                            EvidenceBundleSnapshotRecord.snapshot_id
                            == created.snapshot.snapshot_id
                        )
                        .values(refresh_id="illegal-update")
                    )

        with factory() as session, session.begin():
            session.execute(
                sa.text("DELETE FROM review_tasks WHERE task_id = :task_id"),
                {"task_id": TASK_ID},
            )

        with factory() as session, session.begin():
            count = session.scalar(
                sa.select(sa.func.count()).select_from(EvidenceBundleSnapshotRecord)
            )
        assert count == 0
