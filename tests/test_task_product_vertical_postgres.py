from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_repository import PostgresTaskRepository
from app.product.recent_review import RecentReviewRuntimeRequestCompiler
from app.product.recent_review_service import RecentReviewApplicationService
from app.product.run_receipts import FileRunReceiptStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.runtime import RuntimeExecutionFactory
from app.tasks.fingerprint import compute_task_request_fingerprint
from app.tasks.models import (
    PendingReviewTask,
    TaskCapacityPolicy,
    TaskStatus,
)
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reconciliation import RecentReviewTerminalEvidenceVerifier
from tests.test_agent_draft_preparer import demo_summary
from tests.test_agent_runtime import FactoryProbe, RuntimeProvider


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
NOW = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)


class FixtureSummaryBuilder:
    def build(self, **kwargs) -> dict:
        assert kwargs == {
            "game_name": "DemoPlayer",
            "tag_line": "TEST",
            "count": 10,
            "queue": 420,
        }
        return demo_summary()


@contextmanager
def migrated_repository() -> Iterator[PostgresTaskRepository]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; PostgreSQL product vertical runs in CI"
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
        yield PostgresTaskRepository(factory)
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def test_claimed_task_runs_real_offline_application_runtime_harness_and_persists_terminal(
    tmp_path: Path,
):
    with migrated_repository() as repository:
        run_id = "review_product_pg_vertical"
        payload = {
            "riot_id": "DemoPlayer#TEST",
            "count": 10,
            "queue": 420,
            "focus": "survival",
        }
        pending = PendingReviewTask(
            task_id=UUID("70000000-0000-4000-8000-000000000001"),
            run_id=run_id,
            owner_id="owner-vertical",
            idempotency_key="vertical-1",
            request_fingerprint=compute_task_request_fingerprint(
                task_kind="recent_review",
                schema_version="1.0",
                request_payload=payload,
            ),
            request_payload=payload,
            created_at=NOW,
        )
        repository.create_or_replay(
            pending,
            capacity=TaskCapacityPolicy(owner_active_limit=3, global_active_limit=5),
        )
        claimed = repository.claim_next(worker_id="worker-vertical", now=NOW)
        assert claimed is not None and claimed.lease is not None

        provider = RuntimeProvider()
        probe = FactoryProbe()
        composition = RuntimeCompositionRoot.from_directories(
            skills_root="skills",
            prompt_programs_root="prompt_programs",
        )
        runtime = composition.build_runtime(
            runs_root=tmp_path,
            provider=provider,
            execution_factory=RuntimeExecutionFactory(
                knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
                    Path("data/rag_docs")
                ),
                evaluator_factory=probe.evaluator_factory,
                reviser_factory=probe.reviser_factory,
            ),
        )
        application = RecentReviewApplicationService(
            summary_builder=FixtureSummaryBuilder(),
            compiler=RecentReviewRuntimeRequestCompiler(
                composition.skill_catalog,
                run_id_factory=lambda: (_ for _ in ()).throw(
                    AssertionError("SQL run_id must be used")
                ),
            ),
            runtime=runtime,
            receipt_writer=FileRunReceiptStore(tmp_path),
        )
        executor = RecentReviewTaskExecutor(
            application_service=application,
            evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path),
        )

        terminal = executor.execute(claimed)
        assert terminal.run_id == run_id
        assert repository.succeed(
            task_id=claimed.task_id,
            worker_id="worker-vertical",
            lease_generation=claimed.lease.generation,
            lease_token=claimed.lease.private_token,
            now=NOW + timedelta(seconds=1),
            terminal=terminal,
        )

        stored = repository.get_by_task_id(
            owner_id="owner-vertical",
            task_id=claimed.task_id,
        )
        assert stored is not None
        assert stored.status is TaskStatus.SUCCEEDED
        assert stored.publication_status is not None
        assert stored.trace_reference is not None
        assert stored.receipt_reference is not None
        assert stored.artifact_reference is not None
        assert len(provider.requests) == 3
