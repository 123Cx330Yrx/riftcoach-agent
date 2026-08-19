from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.actor import StaticActorContextProvider
from app.api.composition import PostgresReadinessProbe
from app.api.main import create_app
from app.persistence.player_records import PlayerLinkTaskRecord
from app.persistence.player_repository import PostgresPlayerRepository
from app.players.service import PlayerLinkService


ROOT = Path(__file__).resolve().parents[1]


class UnusedTaskService:
    def create(self, command: object) -> object:
        del command
        raise AssertionError("review task service must not be called")

    def get_task(self, *, owner_id: str, task_id: UUID) -> object:
        del owner_id, task_id
        raise AssertionError("review task service must not be called")

    def get_task_by_run_id(self, *, owner_id: str, run_id: str) -> object:
        del owner_id, run_id
        raise AssertionError("review task service must not be called")


class UnusedRunQuery:
    def get_run(self, run_id: str) -> object:
        del run_id
        raise AssertionError("run query must not be called")

    def get_report(self, run_id: str) -> str:
        del run_id
        raise AssertionError("run query must not be called")


@pytest.fixture
def migrated_player_link_api() -> Iterator[
    tuple[TestClient, TestClient, sessionmaker[Session]]
]:
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
    service = PlayerLinkService(
        repository=PostgresPlayerRepository(factory),
    )

    def make_client(owner_id: str) -> TestClient:
        return TestClient(
            create_app(
                task_service=UnusedTaskService(),
                player_link_service=service,
                query_service=UnusedRunQuery(),
                actor_provider=StaticActorContextProvider(
                    owner_id=owner_id,
                    profile="test",
                ),
                readiness_probe=PostgresReadinessProbe(engine),
            )
        )

    try:
        yield make_client("owner-1"), make_client("owner-2"), factory
    finally:
        engine.dispose()
        command.downgrade(config, "base")


def test_postgres_player_link_create_replay_conflict_and_owner_scope(
    migrated_player_link_api: tuple[
        TestClient,
        TestClient,
        sessionmaker[Session],
    ],
) -> None:
    owner, other_owner, factory = migrated_player_link_api
    headers = {"Idempotency-Key": "postgres-link-1"}
    payload = {
        "riot_id": " Demo Player#KR1 ",
        "routing_region": "asia",
        "relationship_role": "self",
    }

    created = owner.post("/player-links", headers=headers, json=payload)
    replayed = owner.post("/player-links", headers=headers, json=payload)
    link_task_id = UUID(created.json()["link_task_id"])

    assert created.status_code == replayed.status_code == 202
    assert created.json()["disposition"] == "created"
    assert replayed.json()["disposition"] == "replayed"
    assert replayed.json()["link_task_id"] == str(link_task_id)
    assert owner.get(f"/player-links/{link_task_id}").json()["status"] == "queued"
    assert other_owner.get(f"/player-links/{link_task_id}").status_code == 404
    assert owner.get("/health/ready").json()["status"] == "ready"

    conflict = owner.post(
        "/player-links",
        headers=headers,
        json={**payload, "relationship_role": "observed"},
    )
    assert conflict.status_code == 409
    assert conflict.json() == {"code": "idempotency_conflict"}

    with factory() as session:
        record = session.scalar(
            sa.select(PlayerLinkTaskRecord).where(
                PlayerLinkTaskRecord.link_task_id == link_task_id
            )
        )
        assert record is not None
        assert record.owner_id == "owner-1"
        assert record.game_name == "Demo Player"
        assert record.tag_line == "KR1"

    public_text = created.text + owner.get(
        f"/player-links/{link_task_id}"
    ).text
    assert "Demo Player" not in public_text
    assert "puuid" not in public_text.lower()


def test_postgres_player_link_api_uses_real_readiness_contract(
    migrated_player_link_api: tuple[
        TestClient,
        TestClient,
        sessionmaker[Session],
    ],
) -> None:
    owner, _other_owner, _factory = migrated_player_link_api

    assert owner.get("/health/ready").status_code == 200
