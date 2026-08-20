from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from datetime import timedelta
from threading import Barrier, Event, current_thread
from typing import TypeVar
from uuid import UUID

import pytest
import sqlalchemy as sa

from app.conversations.models import (
    ConversationRepositoryAppendDisposition,
    ConversationRepositoryCreateDisposition,
    ConversationRepositoryMutationDisposition,
    ConversationStatus,
)
from app.persistence.conversation_records import (
    ConversationMessageRecord,
    ConversationRecord,
)
from app.persistence.conversation_repository import _conversation_create_lock_id
from app.persistence.player_records import OwnerPlayerRelationshipRecord
from tests.test_conversation_repository_postgres import (
    BASE,
    create_conversation,
    migrated_repository,
    pending_conversation,
    pending_message,
    seed_relationship,
)


T = TypeVar("T")


def result_with_timeout(future: Future[T]) -> T:
    try:
        return future.result(timeout=8)
    except TimeoutError:
        pytest.fail("concurrent PostgreSQL conversation operation timed out")


def test_concurrent_same_key_create_has_exactly_one_row() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        barrier = Barrier(2)

        def create(number: int):
            pending = pending_conversation(
                number,
                relationship_id=relationship_id,
                key="concurrent-key",
                fingerprint="a" * 64,
            )
            barrier.wait()
            return repository.create_or_replay_conversation(pending)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(create, number) for number in (1, 2)]
            results = [result_with_timeout(future) for future in futures]

        assert {result.disposition for result in results} == {
            ConversationRepositoryCreateDisposition.CREATED,
            ConversationRepositoryCreateDisposition.REPLAYED,
        }
        conversation_ids = {
            result.conversation.conversation_id
            for result in results
            if result.conversation is not None
        }
        assert len(conversation_ids) == 1
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ConversationRecord)
            ) == 1


def test_concurrent_same_key_different_fingerprints_create_then_conflict() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_1, relationship_1 = seed_relationship(factory, number=1)
        _subject_2, relationship_2 = seed_relationship(factory, number=2)
        barrier = Barrier(2)

        def create(number: int, relationship_id: UUID, fingerprint: str):
            pending = pending_conversation(
                number,
                relationship_id=relationship_id,
                key="conflicting-key",
                fingerprint=fingerprint,
            )
            barrier.wait()
            return repository.create_or_replay_conversation(pending)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(create, 1, relationship_1, "a" * 64),
                executor.submit(create, 2, relationship_2, "b" * 64),
            )
            results = [result_with_timeout(future) for future in futures]

        assert {result.disposition for result in results} == {
            ConversationRepositoryCreateDisposition.CREATED,
            ConversationRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT,
        }
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ConversationRecord)
            ) == 1


def test_unrelated_create_does_not_wait_on_another_request_advisory_lock() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_1, _relationship_1 = seed_relationship(
            factory,
            owner_id="owner-1",
            number=1,
        )
        _subject_2, relationship_2 = seed_relationship(
            factory,
            owner_id="owner-2",
            number=2,
        )
        held_lock = _conversation_create_lock_id("owner-1", "held-key")
        other_lock = _conversation_create_lock_id("owner-2", "other-key")
        assert held_lock != other_lock

        with factory() as blocker:
            with blocker.begin():
                blocker.execute(
                    sa.text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": held_lock},
                )
                with ThreadPoolExecutor(max_workers=1) as executor:
                    created = result_with_timeout(
                        executor.submit(
                            repository.create_or_replay_conversation,
                            pending_conversation(
                                2,
                                owner_id="owner-2",
                                relationship_id=relationship_2,
                                key="other-key",
                            ),
                        )
                    )

        assert (
            created.disposition
            is ConversationRepositoryCreateDisposition.CREATED
        )


def test_two_concurrent_writers_receive_distinct_contiguous_sequence_numbers() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )
        barrier = Barrier(2)

        def append(number: int):
            pending = pending_message(
                number,
                conversation_id=conversation.conversation_id,
            )
            barrier.wait()
            return repository.append_user_message(pending)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(append, number) for number in (1, 2)]
            results = [result_with_timeout(future) for future in futures]

        assert all(
            result.disposition is ConversationRepositoryAppendDisposition.CREATED
            for result in results
        )
        assert {
            result.message.sequence_no
            for result in results
            if result.message is not None
        } == {1, 2}
        with factory() as session:
            stored = session.get(ConversationRecord, conversation.conversation_id)
            assert stored is not None
            assert stored.next_message_sequence == 3
            rows = session.scalars(
                sa.select(ConversationMessageRecord)
                .where(
                    ConversationMessageRecord.conversation_id
                    == conversation.conversation_id
                )
                .order_by(ConversationMessageRecord.sequence_no.asc())
            ).all()
            assert [row.sequence_no for row in rows] == [1, 2]


def test_relationship_hide_commits_before_waiting_create_and_blocks_it() -> None:
    with migrated_repository() as (repository, factory, _engine):
        _subject_id, relationship_id = seed_relationship(factory)
        row_locked = Barrier(2)

        def hide_relationship() -> None:
            with factory() as session:
                with session.begin():
                    relationship = session.scalar(
                        sa.select(OwnerPlayerRelationshipRecord)
                        .where(
                            OwnerPlayerRelationshipRecord.relationship_id
                            == relationship_id
                        )
                        .with_for_update()
                    )
                    assert relationship is not None
                    relationship.status = "hidden"
                    relationship.hidden_at = BASE + timedelta(minutes=1)
                    relationship.updated_at = BASE + timedelta(minutes=1)
                    row_locked.wait()

        with ThreadPoolExecutor(max_workers=2) as executor:
            hidden_future = executor.submit(hide_relationship)
            row_locked.wait()
            created_future = executor.submit(
                repository.create_or_replay_conversation,
                pending_conversation(1, relationship_id=relationship_id),
            )
            result_with_timeout(hidden_future)
            created = result_with_timeout(created_future)

        assert (
            created.disposition
            is ConversationRepositoryCreateDisposition.RELATIONSHIP_UNAVAILABLE
        )
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(ConversationRecord)
            ) == 0


@pytest.mark.parametrize(
    ("mutation_name", "expected_status", "rejected_append"),
    (
        (
            "archive_conversation",
            ConversationStatus.ARCHIVED,
            ConversationRepositoryAppendDisposition.ARCHIVED,
        ),
        (
            "hide_conversation",
            ConversationStatus.HIDDEN,
            ConversationRepositoryAppendDisposition.NOT_FOUND,
        ),
    ),
    ids=("archive", "hide"),
)
@pytest.mark.parametrize(
    "append_first",
    (True, False),
    ids=("append-first", "lifecycle-first"),
)
def test_lifecycle_and_append_follow_the_forced_lock_order(
    mutation_name: str,
    expected_status: ConversationStatus,
    rejected_append: ConversationRepositoryAppendDisposition,
    append_first: bool,
) -> None:
    with migrated_repository() as (repository, factory, engine):
        _subject_id, relationship_id = seed_relationship(factory)
        conversation = create_conversation(
            repository,
            relationship_id=relationship_id,
        )
        first_relationship_locked = Event()
        second_relationship_attempted = Event()
        first_thread_prefix = "conversation-lock-first"
        second_thread_prefix = "conversation-lock-second"

        def is_relationship_lock(statement: str) -> bool:
            normalized = " ".join(statement.lower().split())
            return (
                "owner_player_relationships" in normalized
                and "for update" in normalized
            )

        def after_cursor_execute(
            _connection,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ) -> None:
            if (
                current_thread().name.startswith(first_thread_prefix)
                and is_relationship_lock(statement)
            ):
                first_relationship_locked.set()

        def before_cursor_execute(
            _connection,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ) -> None:
            if (
                current_thread().name.startswith(second_thread_prefix)
                and is_relationship_lock(statement)
            ):
                second_relationship_attempted.set()

        def append():
            return repository.append_user_message(
                pending_message(1, conversation_id=conversation.conversation_id)
            )

        def mutate():
            mutation = getattr(repository, mutation_name)
            return mutation(
                owner_id="owner-1",
                conversation_id=conversation.conversation_id,
                now=BASE + timedelta(minutes=2),
            )

        first_operation = append if append_first else mutate
        second_operation = mutate if append_first else append
        first_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=first_thread_prefix,
        )
        second_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=second_thread_prefix,
        )

        with factory() as blocker:
            blocker_transaction = blocker.begin()
            blocker.scalar(
                sa.select(ConversationRecord)
                .where(
                    ConversationRecord.conversation_id
                    == conversation.conversation_id
                )
                .with_for_update()
            )
            sa.event.listen(engine, "after_cursor_execute", after_cursor_execute)
            sa.event.listen(engine, "before_cursor_execute", before_cursor_execute)
            try:
                first_future = first_executor.submit(first_operation)
                assert first_relationship_locked.wait(timeout=8), (
                    "first operation did not acquire the relationship lock"
                )
                second_future = second_executor.submit(second_operation)
                assert second_relationship_attempted.wait(timeout=8), (
                    "second operation did not attempt the relationship lock"
                )
                assert not second_future.done(), (
                    "second operation bypassed the held relationship lock"
                )
                blocker_transaction.commit()
                first_result = result_with_timeout(first_future)
                second_result = result_with_timeout(second_future)
            finally:
                if blocker_transaction.is_active:
                    blocker_transaction.rollback()
                sa.event.remove(
                    engine,
                    "after_cursor_execute",
                    after_cursor_execute,
                )
                sa.event.remove(
                    engine,
                    "before_cursor_execute",
                    before_cursor_execute,
                )
                first_executor.shutdown(wait=True, cancel_futures=True)
                second_executor.shutdown(wait=True, cancel_futures=True)

        append_result = first_result if append_first else second_result
        mutation_result = second_result if append_first else first_result
        assert (
            mutation_result.disposition
            is ConversationRepositoryMutationDisposition.UPDATED
        )
        expected_append = (
            ConversationRepositoryAppendDisposition.CREATED
            if append_first
            else rejected_append
        )
        assert append_result.disposition is expected_append

        with factory() as session:
            stored = session.get(ConversationRecord, conversation.conversation_id)
            assert stored is not None
            assert stored.status == expected_status.value
            message_count = session.scalar(
                sa.select(sa.func.count())
                .select_from(ConversationMessageRecord)
                .where(
                    ConversationMessageRecord.conversation_id
                    == conversation.conversation_id
                )
            )
            expected_count = 1 if append_first else 0
            assert message_count == expected_count
            assert stored.next_message_sequence == expected_count + 1
