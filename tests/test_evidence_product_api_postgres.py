from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.actor import StaticActorContextProvider
from app.api.composition import PostgresReadinessProbe
from app.api.main import create_app
from app.evidence.service import EvidenceProductService
from app.evidence.storage import PendingEvidenceBundleSnapshot
from app.persistence.evidence_snapshot_repository import (
    PostgresEvidenceSnapshotRepository,
)
from app.persistence.task_repository import PostgresTaskRepository
from app.product.run_query import RunQueryService
from app.tasks.service import ReviewTaskService
from tests.player_link_api_stubs import UnusedPlayerLinkService
from tests.test_evidence_snapshot_contracts import bundle


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migrated_product_api(
    tmp_path: Path,
) -> Iterator[
    tuple[
        TestClient,
        TestClient,
        PostgresTaskRepository,
        PostgresEvidenceSnapshotRepository,
    ]
]:
    url = os.getenv("RIFTCOACH_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RIFTCOACH_TEST_DATABASE_URL is not configured")
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine: Engine = create_engine(url, pool_pre_ping=True)
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
    tasks = PostgresTaskRepository(factory)
    evidence = PostgresEvidenceSnapshotRepository(factory)
    task_service = ReviewTaskService(repository=tasks)
    products = EvidenceProductService(
        task_service=task_service,
        repository=evidence,
    )

    def make_client(owner_id: str) -> TestClient:
        return TestClient(
            create_app(
                task_service=task_service,
                player_link_service=UnusedPlayerLinkService(),
                query_service=RunQueryService(tmp_path),
                actor_provider=StaticActorContextProvider(
                    owner_id=owner_id,
                    profile="test",
                ),
                readiness_probe=PostgresReadinessProbe(engine),
                evidence_product_service=products,
            )
        )

    try:
        yield make_client("owner-1"), make_client("owner-2"), tasks, evidence
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def test_real_postgres_snapshot_reaches_owner_scoped_product_http(
    migrated_product_api,
) -> None:
    owner, other, tasks, evidence = migrated_product_api
    created = owner.post(
        "/reviews/recent",
        headers={"Idempotency-Key": "evidence-product-postgres-1"},
        json={
            "riot_id": "DemoPlayer#TEST",
            "routing_region": "asia",
            "focus": "overall",
        },
    )
    task_id = UUID(created.json()["task_id"])
    run_id = created.json()["run_id"]
    claimed = tasks.claim_next(
        worker_id="evidence-product-worker",
        now=datetime.now(timezone.utc),
    )
    assert claimed is not None and claimed.task_id == task_id
    written = evidence.append(
        PendingEvidenceBundleSnapshot(
            task_id=task_id,
            run_id=run_id,
            owner_id="owner-1",
            refresh_id="postgres-vertical-1",
            bundle=bundle(),
            stored_at=datetime.now(timezone.utc),
        )
    )

    evidence_response = owner.get(f"/runs/{run_id}/evidence")
    state_response = owner.get(f"/runs/{run_id}/product-state")

    assert created.status_code == 202
    assert written.snapshot.revision == 1
    assert evidence_response.status_code == 200
    assert evidence_response.json()["revision"] == 1
    assert state_response.status_code == 200
    assert state_response.json()["state"] == "not_ready"
    assert other.get(f"/runs/{run_id}/evidence").status_code == 404
    assert other.get(f"/runs/{run_id}/product-state").status_code == 404
    serialized = evidence_response.text.lower()
    for forbidden in ("owner_id", "refresh_id", "puuid", "request_payload"):
        assert forbidden not in serialized
