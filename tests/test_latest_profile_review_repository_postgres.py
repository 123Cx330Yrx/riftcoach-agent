from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.persistence.config import DatabaseSettings
from app.persistence.conversation_records import ConversationRecord
from app.persistence.database import build_engine, build_session_factory
from app.persistence.latest_review_repository import (
    PostgresLatestProfileReviewRepository,
)
from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerLinkTaskRecord,
    PlayerSubjectRecord,
)
from app.persistence.task_record import ReviewTaskRecord
from app.product.latest_review import LatestProfileReviewRepositoryError
from app.tasks.models import TaskPublicationStatus, TaskStatus


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
NOW = datetime(2026, 8, 23, 10, 0, 0, tzinfo=timezone.utc)


def config() -> Config:
    value = Config(str(ROOT / "alembic.ini"))
    value.set_main_option("script_location", str(ROOT / "migrations"))
    return value


@pytest.fixture()
def database(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[sa.Engine, object]]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL locator "
            "evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")
    monkeypatch.setenv("DATABASE_URL", url)
    command.downgrade(config(), "base")
    command.upgrade(config(), "head")
    engine = build_engine(DatabaseSettings(url=url))
    factory = build_session_factory(engine)
    try:
        yield engine, factory
    finally:
        engine.dispose()
        command.downgrade(config(), "base")


def seed_profile(
    factory,
    *,
    owner_id: str = "latest-owner",
    role: str = "self",
    relationship_status: str = "active",
    successful_link: bool = True,
) -> dict[str, object]:
    profile_id = uuid4()
    subject_id = uuid4()
    conversation_id = uuid4()
    with factory() as session:
        with session.begin():
            session.add(
                PlayerSubjectRecord(
                    player_subject_id=subject_id,
                    game="lol",
                    puuid=f"PUUID_{uuid4().hex}",
                    current_routing_region="asia",
                    created_at=NOW,
                    updated_at=NOW,
                    last_resolved_at=NOW,
                )
            )
            session.flush()
            session.add(
                OwnerPlayerRelationshipRecord(
                    relationship_id=profile_id,
                    owner_id=owner_id,
                    player_subject_id=subject_id,
                    relationship_role=role,
                    verification_status=(
                        "unverified_claim" if role == "self" else "not_applicable"
                    ),
                    status=relationship_status,
                    created_at=NOW,
                    updated_at=NOW,
                    hidden_at=(
                        NOW if relationship_status == "hidden" else None
                    ),
                )
            )
            session.flush()
            if successful_link:
                session.add(
                    PlayerLinkTaskRecord(
                        link_task_id=uuid4(),
                        task_kind="player_link",
                        schema_version="1.0",
                        owner_id=owner_id,
                        worker_id="locator-worker",
                        idempotency_key=f"link-{profile_id}",
                        request_fingerprint=uuid4().hex * 2,
                        game_name="Latest Player",
                        tag_line="TEST",
                        routing_region="asia",
                        relationship_role=role,
                        alias_hash=uuid4().hex * 2,
                        status="succeeded",
                        created_at=NOW,
                        updated_at=NOW + timedelta(seconds=2),
                        claimed_at=NOW + timedelta(seconds=1),
                        finished_at=NOW + timedelta(seconds=2),
                        terminal_reason=None,
                        confirmed_game_name="Latest Player",
                        confirmed_tag_line="TEST",
                        player_subject_id=subject_id,
                        relationship_id=profile_id,
                    )
                )
            session.add(
                ConversationRecord(
                    conversation_id=conversation_id,
                    schema_version="1.0",
                    owner_id=owner_id,
                    relationship_id=profile_id,
                    player_subject_id=subject_id,
                    relationship_role=role,
                    idempotency_key=f"conversation-{conversation_id}",
                    request_fingerprint=uuid4().hex * 2,
                    status="active",
                    next_message_sequence=1,
                    created_at=NOW,
                    updated_at=NOW,
                    last_message_at=None,
                    hidden_at=None,
                )
            )
    return {
        "owner_id": owner_id,
        "profile_id": profile_id,
        "subject_id": subject_id,
        "conversation_id": conversation_id,
        "role": role,
    }


def insert_review(
    factory,
    values: dict[str, object],
    *,
    task_id: UUID | None = None,
    created_at: datetime = NOW + timedelta(minutes=1),
    status: str = "queued",
    schema_version: str = "2.0",
    task_kind: str = "recent_review",
    relationship_id: UUID | None = None,
) -> UUID:
    selected_task_id = task_id or uuid4()
    claimed_at = created_at + timedelta(seconds=1) if status in {"failed", "succeeded"} else None
    finished_at = created_at + timedelta(seconds=2) if status in {"failed", "succeeded"} else None
    succeeded = status == "succeeded"
    with factory() as session:
        with session.begin():
            session.add(
                ReviewTaskRecord(
                    task_id=selected_task_id,
                    run_id=f"latest_{selected_task_id.hex}",
                    task_kind=task_kind,
                    schema_version=schema_version,
                    owner_id=str(values["owner_id"]),
                    idempotency_key=f"review-{selected_task_id}",
                    request_fingerprint=selected_task_id.hex * 2,
                    request_payload={"count": 5},
                    conversation_id=(
                        values["conversation_id"] if schema_version == "2.0" else None
                    ),
                    relationship_id=(
                        relationship_id or values["profile_id"]
                        if schema_version == "2.0"
                        else None
                    ),
                    player_subject_id=(
                        values["subject_id"] if schema_version == "2.0" else None
                    ),
                    relationship_role=(
                        values["role"] if schema_version == "2.0" else None
                    ),
                    status=status,
                    worker_id=("locator-worker" if claimed_at is not None else None),
                    created_at=created_at,
                    updated_at=finished_at or created_at,
                    claimed_at=claimed_at,
                    finished_at=finished_at,
                    terminal_reason=(
                        "quality_gate_passed" if succeeded else "execution_failed"
                    ) if finished_at is not None else None,
                    publication_status=("published" if succeeded else None),
                    report_available=succeeded,
                    trace_reference=None,
                    receipt_reference=None,
                    artifact_reference=None,
                )
            )
    return selected_task_id


def test_visible_profile_without_review_returns_legal_null(database) -> None:
    _engine, factory = database
    values = seed_profile(factory)
    repository = PostgresLatestProfileReviewRepository(factory)

    assert repository.get_latest(
        owner_id=str(values["owner_id"]),
        player_profile_id=values["profile_id"],
    ) is None


def test_cross_owner_hidden_and_unresolved_profiles_are_not_found(database) -> None:
    _engine, factory = database
    visible = seed_profile(factory)
    hidden = seed_profile(factory, owner_id="hidden-owner", relationship_status="hidden")
    unresolved = seed_profile(factory, owner_id="unresolved-owner", successful_link=False)
    repository = PostgresLatestProfileReviewRepository(factory)

    checks = (
        ("other-owner", visible["profile_id"]),
        (hidden["owner_id"], hidden["profile_id"]),
        (unresolved["owner_id"], unresolved["profile_id"]),
    )
    for owner_id, profile_id in checks:
        with pytest.raises(LatestProfileReviewRepositoryError) as caught:
            repository.get_latest(
                owner_id=str(owner_id),
                player_profile_id=profile_id,
            )
        assert caught.value.code == "player_profile_not_found"


def test_latest_failed_task_is_not_skipped_for_older_success(database) -> None:
    _engine, factory = database
    values = seed_profile(factory)
    insert_review(
        factory,
        values,
        created_at=NOW + timedelta(minutes=1),
        status="succeeded",
    )
    failed_id = insert_review(
        factory,
        values,
        created_at=NOW + timedelta(minutes=2),
        status="failed",
    )

    latest = PostgresLatestProfileReviewRepository(factory).get_latest(
        owner_id=str(values["owner_id"]),
        player_profile_id=values["profile_id"],
    )

    assert latest is not None
    assert latest.task_id == failed_id
    assert latest.status is TaskStatus.FAILED
    assert latest.publication_status is None
    assert latest.report_available is False


def test_legacy_wrong_kind_and_wrong_relationship_are_excluded(database) -> None:
    _engine, factory = database
    selected = seed_profile(factory)
    other = seed_profile(factory, owner_id=str(selected["owner_id"]))
    insert_review(
        factory,
        selected,
        schema_version="1.0",
        created_at=NOW + timedelta(minutes=4),
    )
    insert_review(
        factory,
        selected,
        task_kind="future_review",
        created_at=NOW + timedelta(minutes=3),
    )
    insert_review(
        factory,
        other,
        created_at=NOW + timedelta(minutes=2),
    )
    selected_id = insert_review(
        factory,
        selected,
        created_at=NOW + timedelta(minutes=1),
    )

    latest = PostgresLatestProfileReviewRepository(factory).get_latest(
        owner_id=str(selected["owner_id"]),
        player_profile_id=selected["profile_id"],
    )

    assert latest is not None and latest.task_id == selected_id


def test_same_timestamp_uses_task_id_descending_as_stable_tie_break(database) -> None:
    _engine, factory = database
    values = seed_profile(factory)
    low = UUID("93000000-0000-4000-8000-000000000001")
    high = UUID("93000000-0000-4000-8000-000000000002")
    insert_review(factory, values, task_id=low)
    insert_review(factory, values, task_id=high)

    latest = PostgresLatestProfileReviewRepository(factory).get_latest(
        owner_id=str(values["owner_id"]),
        player_profile_id=values["profile_id"],
    )

    assert latest is not None and latest.task_id == high
    assert latest.status is TaskStatus.QUEUED


def test_invalid_identity_is_rejected_before_opening_a_session() -> None:
    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        raise AssertionError("invalid identity must not open PostgreSQL")

    repository = PostgresLatestProfileReviewRepository(factory)
    with pytest.raises(TypeError):
        repository.get_latest(
            owner_id="owner/private",
            player_profile_id=UUID("94000000-0000-4000-8000-000000000001"),
        )
    assert calls == 0
