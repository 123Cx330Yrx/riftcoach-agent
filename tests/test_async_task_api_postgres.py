from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.actor import StaticActorContextProvider
from app.api.composition import PostgresReadinessProbe
from app.api.main import create_app
from app.persistence.task_repository import PostgresTaskRepository
from app.product.run_query import RunQueryService
from app.tasks.service import ReviewTaskService
from tests.player_link_api_stubs import UnusedPlayerLinkService


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migrated_api(tmp_path: Path) -> Iterator[tuple[TestClient, TestClient]]:
    url = os.getenv("RIFTCOACH_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RIFTCOACH_TEST_DATABASE_URL is not configured")

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
    repository = PostgresTaskRepository(factory)

    def make_client(owner_id: str) -> TestClient:
        return TestClient(
            create_app(
                task_service=ReviewTaskService(repository=repository),
                player_link_service=UnusedPlayerLinkService(),
                query_service=RunQueryService(tmp_path),
                actor_provider=StaticActorContextProvider(
                    owner_id=owner_id,
                    profile="test",
                ),
                readiness_probe=PostgresReadinessProbe(engine),
            )
        )

    try:
        yield make_client("owner-1"), make_client("owner-2")
    finally:
        engine.dispose()
        command.downgrade(config, "base")


def test_postgres_api_create_replay_owner_scope_and_not_ready_run(
    migrated_api: tuple[TestClient, TestClient],
) -> None:
    owner, other_owner = migrated_api
    headers = {"Idempotency-Key": "api-request-1"}
    payload = {"riot_id": "DemoPlayer#TEST", "focus": "survival"}

    created = owner.post("/reviews/recent", headers=headers, json=payload)
    replayed = owner.post("/reviews/recent", headers=headers, json=payload)
    task_id = created.json()["task_id"]
    run_id = created.json()["run_id"]

    assert created.status_code == replayed.status_code == 202
    assert created.json()["disposition"] == "created"
    assert replayed.json()["disposition"] == "replayed"
    assert replayed.json()["task_id"] == task_id
    assert replayed.json()["run_id"] == run_id
    assert owner.get(f"/tasks/{task_id}").json()["status"] == "queued"
    assert other_owner.get(f"/tasks/{task_id}").status_code == 404
    assert other_owner.get(f"/runs/{run_id}").status_code == 404
    assert owner.get(f"/runs/{run_id}").status_code == 409
    assert owner.get(f"/runs/{run_id}/report").status_code == 409
    assert owner.get("/health/ready").json()["status"] == "ready"
