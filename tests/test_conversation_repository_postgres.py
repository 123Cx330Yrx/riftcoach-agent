from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from app.conversations.models import (
    ConversationRepositoryAppendDisposition,
    ConversationRepositoryCreateDisposition,
    ConversationRepositoryListDisposition,
    ConversationRepositoryMutationDisposition,
    ConversationStatus,
    PendingConversation,
    PendingUserMessage,
    RelationshipRole,
    compute_message_content_sha256,
)
from app.conversations.ports import ConversationRepositoryError
from app.persistence.config import DatabaseSettings
from app.persistence.conversation_records import (
    ConversationMessageRecord,
    ConversationRecord,
)
from app.persistence import conversation_repository as conversation_repository_module
from app.persistence.conversation_repository import PostgresConversationRepository
from app.persistence.database import build_engine, build_session_factory
from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerSubjectRecord,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)


def test_conversation_create_advisory_lock_is_scoped_and_stable() -> None:
    lock_id = getattr(
        conversation_repository_module,
        "_conversation_create_lock_id",
    )

    first = lock_id("owner-1", "request-1")

    assert first == lock_id("owner-1", "request-1")
    assert first != lock_id("owner-1", "request-2")
    assert first != lock_id("owner-2", "request-1")
    assert -(2**63) <= first < 2**63


@contextmanager
def migrated_repository():
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL "
            "conversation repository evidence runs in CI"
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
        yield PostgresConversationRepository(factory), factory, engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def seed_relationship(
    factory: sessionmaker[Session],
    *,
    owner_id: str = "owner-1",
    number: int = 1,
    role: RelationshipRole = RelationshipRole.SELF,
) -> tuple[UUID, UUID]:
    subject_id = UUID(f"71000000-0000-4000-8000-{number:012d}")
    relationship_id = UUID(f"72000000-0000-4000-8000-{number:012d}")
    verification = (
        "unverified_claim"
        if role is RelationshipRole.SELF
        else "not_applicable"
    )
    with factory.begin() as session:
        session.add(
            PlayerSubjectRecord(
                player_subject_id=subject_id,
                game="lol",
                puuid=f"PUUID_CONVERSATION_{number}",
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
    return subject_id, relationship_id


def pending_conversation(
    number: int,
    *,
    owner_id: str = "owner-1",
    relationship_id: UUID,
    key: str | None = None,
    fingerprint: str | None = None,
) -> PendingConversation:
    return PendingConversation(
        conversation_id=UUID(f"73000000-0000-4000-8000-{number:012d}"),
        owner_id=owner_id,
        idempotency_key=key or f"conversation-{number}",
        relationship_id=relationship_id,
        request_fingerprint=fingerprint or f"{number:064x}",
        created_at=BASE + timedelta(seconds=number),
    )


def pending_message(
    number: int,
    *,
    conversation_id: UUID,
    owner_id: str = "owner-1",
    message_id: UUID | None = None,
    content: str | None = None,
) -> PendingUserMessage:
    body = content or f"message {number}"
    return PendingUserMessage(
        message_id=message_id
        or UUID(f"74000000-0000-4000-8000-{number:012d}"),
        owner_id=owner_id,
        conversation_id=conversation_id,
        content=body,
        content_sha256=compute_message_content_sha256(body),
        created_at=BASE + timedelta(minutes=1, seconds=number),
    )


def create_conversation(
    repository: PostgresConversationRepository,
    *,
    relationship_id: UUID,
    number: int = 1,
):
    result = repository.create_or_replay_conversation(
        pending_conversation(number, relationship_id=relationship_id)
    )
    assert result.disposition is ConversationRepositoryCreateDisposition.CREATED
    assert result.conversation is not None
    return result.conversation


def test_create_replays_original_identity_and_conflict_is_non_mutating() -> None:
    with migrated_repository() as (repository, factory, _engine):
        subject_id, relationship_id = seed_relationship(factory)
        original = pending_conversation(
            1,
            relationship_id=relationship_id,
            key="same-key",
            fingerprint="a" * 64,
        )
        alternate = pending_conversation(
            2,
            relationship_id=relationship_id,
            key="same-key",
            fingerprint="a" * 64,
        )

        created = repository.create_or_replay_conversation(original)
        replayed = repository.create_or_replay_conversation(alternate)
        conflict = repository.create_or_replay_conversation(
            pending_conversation(
                3,
                relationship_id=relationship_id,
                key="same-key",
                fingerprint="b" * 64,
            )
        )

        assert created.disposition is ConversationRepositoryCreateDisposition.CREATED
        assert replayed.disposition is ConversationRepositoryCreateDisposition.REPLAYED
        assert replayed.conversation == created.conversation
        assert (
            conflict.disposition
            is ConversationRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
        )
        assert conflict.conversation is None
        assert created.conversation is not None
        assert created.conversation.player_subject_id == subject_id
        assert created.conversation.relationship_role is RelationshipRole.SELF
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ConversationRecord)
            ) == 1


def test_create_requires_owner_scoped_active_relationship() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)

        wrong_owner = repository.create_or_replay_conversation(
            pending_conversation(
                1,
                owner_id="owner-2",
                relationship_id=relationship_id,
            )
        )
        with factory.begin() as session:
            relationship = session.get(
                OwnerPlayerRelationshipRecord,
                relationship_id,
            )
            assert relationship is not None
            relationship.status = "hidden"
            relationship.hidden_at = BASE + timedelta(minutes=2)
            relationship.updated_at = BASE + timedelta(minutes=2)
        hidden = repository.create_or_replay_conversation(
            pending_conversation(2, relationship_id=relationship_id)
        )

        assert (
            wrong_owner.disposition
            is ConversationRepositoryCreateDisposition.RELATIONSHIP_UNAVAILABLE
        )
        assert (
            hidden.disposition
            is ConversationRepositoryCreateDisposition.RELATIONSHIP_UNAVAILABLE
        )
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ConversationRecord)
            ) == 0


def test_same_key_is_isolated_by_owner() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_1, relationship_1 = seed_relationship(
            factory,
            owner_id="owner-1",
            number=1,
        )
        _subject_2, relationship_2 = seed_relationship(
            factory,
            owner_id="owner-2",
            number=2,
        )
        first = repository.create_or_replay_conversation(
            pending_conversation(
                1,
                owner_id="owner-1",
                relationship_id=relationship_1,
                key="shared-key",
            )
        )
        second = repository.create_or_replay_conversation(
            pending_conversation(
                2,
                owner_id="owner-2",
                relationship_id=relationship_2,
                key="shared-key",
            )
        )

        assert first.disposition is ConversationRepositoryCreateDisposition.CREATED
        assert second.disposition is ConversationRepositoryCreateDisposition.CREATED
        assert first.conversation is not None
        assert second.conversation is not None
        assert first.conversation.owner_id != second.conversation.owner_id


def test_get_and_all_writes_hide_unowned_or_hidden_relationship() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )

        assert repository.get_conversation(
            owner_id="owner-2",
            conversation_id=conversation.conversation_id,
        ) is None
        with factory.begin() as session:
            relationship = session.get(
                OwnerPlayerRelationshipRecord,
                relationship_id,
            )
            assert relationship is not None
            relationship.status = "hidden"
            relationship.hidden_at = BASE + timedelta(minutes=2)
            relationship.updated_at = BASE + timedelta(minutes=2)

        assert repository.get_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
        ) is None
        appended = repository.append_user_message(
            pending_message(1, conversation_id=conversation.conversation_id)
        )
        listed = repository.list_messages(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            after_sequence=0,
            limit=10,
        )
        archived = repository.archive_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            now=BASE + timedelta(minutes=3),
        )
        hidden = repository.hide_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            now=BASE + timedelta(minutes=3),
        )

        assert appended.disposition is ConversationRepositoryAppendDisposition.NOT_FOUND
        assert listed.disposition is ConversationRepositoryListDisposition.NOT_FOUND
        assert archived.disposition is ConversationRepositoryMutationDisposition.NOT_FOUND
        assert hidden.disposition is ConversationRepositoryMutationDisposition.NOT_FOUND


def test_append_allocates_sequence_and_bounded_cursor_list_is_stable() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )
        first = repository.append_user_message(
            pending_message(
                1,
                conversation_id=conversation.conversation_id,
                content="  keep exact \n",
            )
        )
        second = repository.append_user_message(
            pending_message(2, conversation_id=conversation.conversation_id)
        )

        assert first.disposition is ConversationRepositoryAppendDisposition.CREATED
        assert second.disposition is ConversationRepositoryAppendDisposition.CREATED
        assert first.message is not None
        assert second.message is not None
        assert first.message.sequence_no == 1
        assert second.message.sequence_no == 2
        assert first.message.content == "  keep exact \n"

        page_one = repository.list_messages(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            after_sequence=0,
            limit=1,
        )
        page_two = repository.list_messages(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            after_sequence=1,
            limit=10,
        )
        assert page_one.disposition is ConversationRepositoryListDisposition.FOUND
        assert [item.sequence_no for item in page_one.messages] == [1]
        assert page_one.has_more is True
        assert [item.sequence_no for item in page_two.messages] == [2]
        assert page_two.has_more is False

        with factory() as session:
            stored = session.get(ConversationRecord, conversation.conversation_id)
            assert stored is not None
            assert stored.next_message_sequence == 3
            assert stored.last_message_at == second.message.created_at


def test_append_failure_rolls_back_counter_and_message_together() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )
        duplicate_id = UUID("74000000-0000-4000-8000-000000009999")
        first = repository.append_user_message(
            pending_message(
                1,
                conversation_id=conversation.conversation_id,
                message_id=duplicate_id,
            )
        )
        assert first.message is not None

        with pytest.raises(ConversationRepositoryError) as failed:
            repository.append_user_message(
                pending_message(
                    2,
                    conversation_id=conversation.conversation_id,
                    message_id=duplicate_id,
                )
            )
        assert failed.value.args == ("conversation_repository_integrity_failed",)

        recovered = repository.append_user_message(
            pending_message(3, conversation_id=conversation.conversation_id)
        )
        assert recovered.message is not None
        assert recovered.message.sequence_no == 2
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ConversationMessageRecord)
            ) == 2
            stored = session.get(ConversationRecord, conversation.conversation_id)
            assert stored is not None
            assert stored.next_message_sequence == 3


def test_archive_is_readable_idempotent_and_hide_is_irreversible_visibility() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )
        archived = repository.archive_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            now=BASE + timedelta(minutes=2),
        )
        replayed = repository.archive_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            now=BASE + timedelta(minutes=3),
        )
        rejected = repository.append_user_message(
            pending_message(1, conversation_id=conversation.conversation_id)
        )

        assert archived.disposition is ConversationRepositoryMutationDisposition.UPDATED
        assert replayed.disposition is ConversationRepositoryMutationDisposition.REPLAYED
        assert rejected.disposition is ConversationRepositoryAppendDisposition.ARCHIVED
        readable = repository.get_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
        )
        assert readable is not None
        assert readable.status is ConversationStatus.ARCHIVED

        hidden = repository.hide_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            now=BASE + timedelta(minutes=4),
        )
        assert hidden.disposition is ConversationRepositoryMutationDisposition.UPDATED
        assert hidden.conversation is not None
        assert hidden.conversation.status is ConversationStatus.HIDDEN
        assert repository.get_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
        ) is None
        second_hide = repository.hide_conversation(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            now=BASE + timedelta(minutes=5),
        )
        assert second_hide.disposition is ConversationRepositoryMutationDisposition.NOT_FOUND


def test_cross_subject_message_insert_is_rejected_by_composite_fk() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory, number=1)
        other_subject_id, _other_relationship = seed_relationship(
            factory,
            number=2,
        )
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )

        with pytest.raises(sa.exc.IntegrityError):
            with factory.begin() as session:
                session.add(
                    ConversationMessageRecord(
                        message_id=UUID(
                            "74000000-0000-4000-8000-000000008888"
                        ),
                        conversation_id=conversation.conversation_id,
                        owner_id=conversation.owner_id,
                        relationship_id=conversation.relationship_id,
                        player_subject_id=other_subject_id,
                        relationship_role=conversation.relationship_role.value,
                        sequence_no=1,
                        role="user",
                        content="wrong subject",
                        content_sha256=compute_message_content_sha256(
                            "wrong subject"
                        ),
                        source_task_id=None,
                        source_run_id=None,
                        created_at=BASE + timedelta(minutes=1),
                        hidden_at=None,
                    )
                )


def test_hidden_messages_are_filtered_from_ordered_page() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )
        first = repository.append_user_message(
            pending_message(1, conversation_id=conversation.conversation_id)
        )
        second = repository.append_user_message(
            pending_message(2, conversation_id=conversation.conversation_id)
        )
        assert first.message is not None
        assert second.message is not None
        with factory.begin() as session:
            record = session.get(ConversationMessageRecord, first.message.message_id)
            assert record is not None
            record.hidden_at = BASE + timedelta(minutes=5)

        page = repository.list_messages(
            owner_id="owner-1",
            conversation_id=conversation.conversation_id,
            after_sequence=0,
            limit=10,
        )
        assert [item.sequence_no for item in page.messages] == [2]


def test_repository_maps_database_and_integrity_failures_to_safe_codes() -> None:
    class BrokenFactory:
        def __call__(self):
            raise sa.exc.OperationalError("SELECT secret", {}, RuntimeError("secret"))

    repository = PostgresConversationRepository(BrokenFactory())
    with pytest.raises(ConversationRepositoryError) as failure:
        repository.get_conversation(
            owner_id="owner-1",
            conversation_id=UUID("73000000-0000-4000-8000-000000000001"),
        )
    assert failure.value.args == ("conversation_repository_unavailable",)
