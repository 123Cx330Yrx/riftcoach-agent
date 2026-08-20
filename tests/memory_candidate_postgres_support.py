from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.memory.models import (
    CandidateKind,
    MemoryOperation,
    PendingMemoryCandidate,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
)
from app.persistence.config import DatabaseSettings
from app.persistence.conversation_records import ConversationRecord
from app.persistence.database import build_engine, build_session_factory
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from app.persistence.player_records import OwnerPlayerRelationshipRecord, PlayerSubjectRecord


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2026, 8, 20, 14, 0, tzinfo=timezone.utc)


@contextmanager
def migrated_memory_repository():
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL memory evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = build_engine(DatabaseSettings(url=url))
    factory = build_session_factory(engine)
    try:
        yield PostgresMemoryCandidateRepository(factory), factory, engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


def seed_conversation(
    factory: sessionmaker[Session],
    *,
    number: int = 1,
    owner_id: str = "memory-owner",
    role: RelationshipRole = RelationshipRole.SELF,
) -> tuple[UUID, UUID, UUID]:
    subject_id = UUID(f"81000000-0000-4000-8000-{number:012d}")
    relationship_id = UUID(f"82000000-0000-4000-8000-{number:012d}")
    conversation_id = UUID(f"83000000-0000-4000-8000-{number:012d}")
    verification = "unverified_claim" if role is RelationshipRole.SELF else "not_applicable"
    with factory.begin() as session:
        session.add(
            PlayerSubjectRecord(
                player_subject_id=subject_id,
                game="lol",
                puuid=f"PUUID_MEMORY_{number}",
                current_routing_region="asia",
                created_at=BASE,
                updated_at=BASE,
                last_resolved_at=BASE,
            )
        )
        session.flush()
        session.add(
            OwnerPlayerRelationshipRecord(
                relationship_id=relationship_id,
                owner_id=owner_id,
                player_subject_id=subject_id,
                relationship_role=role.value,
                verification_status=verification,
                status="active",
                created_at=BASE,
                updated_at=BASE,
                hidden_at=None,
            )
        )
        session.flush()
        session.add(
            ConversationRecord(
                conversation_id=conversation_id,
                schema_version="1.0",
                owner_id=owner_id,
                relationship_id=relationship_id,
                player_subject_id=subject_id,
                relationship_role=role.value,
                idempotency_key=f"conversation-{number}",
                request_fingerprint=f"{number:064x}",
                status="active",
                next_message_sequence=1,
                created_at=BASE,
                updated_at=BASE,
                last_message_at=None,
                hidden_at=None,
            )
        )
    return subject_id, relationship_id, conversation_id


def pending_candidate(
    number: int,
    *,
    conversation_id: UUID,
    owner_id: str = "memory-owner",
    key: str | None = None,
    payload: dict[str, object] | None = None,
) -> PendingMemoryCandidate:
    return PendingMemoryCandidate(
        candidate_id=UUID(f"84000000-0000-4000-8000-{number:012d}"),
        owner_id=owner_id,
        conversation_id=conversation_id,
        idempotency_key=key or f"candidate-{number}",
        target_scope=TargetScope.OWNER_GLOBAL,
        candidate_kind=CandidateKind.OWNER_PREFERENCE,
        memory_key="report_language",
        operation=MemoryOperation.SET,
        proposal_payload=payload or {"value": "zh-CN"},
        provenance_kind=ProvenanceKind.USER_STRUCTURED_INPUT,
        producer_id="postgres-test",
        producer_version="1.0.0",
        proposal_confidence=None,
        created_at=BASE + timedelta(seconds=number),
        expires_at=BASE + timedelta(days=30, seconds=number),
    )
