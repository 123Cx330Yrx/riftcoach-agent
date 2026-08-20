from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, current_thread
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.persistence.database import build_session_factory
from app.persistence.conversation_records import ConversationRecord
from app.persistence.conversation_repository import PostgresConversationRepository
from app.persistence.task_record import ReviewTaskRecord
from app.persistence.task_repository import PostgresTaskRepository
from app.conversations.models import ConversationRepositoryMutationDisposition
from app.tasks.models import (
    PendingConversationReviewTask,
    TaskCapacityPolicy,
    TaskRepositoryCreateDisposition,
    TaskStatus,
)
from app.tasks.ports import TaskRepositoryError


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
NOW = datetime(2026, 8, 20, 9, 0, 0, tzinfo=timezone.utc)


def config() -> Config:
    value = Config(str(ROOT / "alembic.ini"))
    value.set_main_option("script_location", str(ROOT / "migrations"))
    return value


@pytest.fixture()
def postgres_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[sa.Engine]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL "
            "Conversation Review Repository evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")
    monkeypatch.setenv("DATABASE_URL", url)
    command.downgrade(config(), "base")
    command.upgrade(config(), "head")
    engine = sa.create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config(), "base")


def seed_conversation(
    engine: sa.Engine,
    *,
    owner_id: str = "owner-review-v2",
    game_name: str = "Initial Name",
) -> dict[str, object]:
    values: dict[str, object] = {
        "owner_id": owner_id,
        "player_subject_id": uuid4(),
        "relationship_id": uuid4(),
        "conversation_id": uuid4(),
        "player_alias_id": uuid4(),
        "puuid": f"PUUID_{uuid4().hex}",
        "game_name": game_name,
    }
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO player_subjects (player_subject_id, game, puuid, "
                "current_routing_region) VALUES (:player_subject_id, 'lol', "
                ":puuid, 'asia')"
            ),
            values,
        )
        connection.execute(
            sa.text(
                "INSERT INTO player_aliases (player_alias_id, player_subject_id, "
                "routing_region, game_name, tag_line, normalized_riot_id_hash, "
                "first_seen_at, last_seen_at) "
                "VALUES (:player_alias_id, :player_subject_id, 'asia', "
                ":game_name, 'KR1', :alias_hash, :seen_at, :seen_at)"
            ),
            {**values, "alias_hash": uuid4().hex * 2, "seen_at": NOW},
        )
        connection.execute(
            sa.text(
                "INSERT INTO owner_player_relationships (relationship_id, owner_id, "
                "player_subject_id, relationship_role, verification_status) VALUES "
                "(:relationship_id, :owner_id, :player_subject_id, 'self', "
                "'unverified_claim')"
            ),
            values,
        )
        connection.execute(
            sa.text(
                "INSERT INTO conversations (conversation_id, owner_id, relationship_id, "
                "player_subject_id, relationship_role, idempotency_key, "
                "request_fingerprint) VALUES (:conversation_id, :owner_id, "
                ":relationship_id, :player_subject_id, 'self', :conversation_key, "
                ":fingerprint)"
            ),
            {
                **values,
                "conversation_key": f"conversation-{values['conversation_id']}",
                "fingerprint": "a" * 64,
            },
        )
    return values


def pending(
    values: dict[str, object],
    *,
    key: str = "review-v2-1",
    task_id: UUID | None = None,
) -> PendingConversationReviewTask:
    selected_task_id = task_id or uuid4()
    return PendingConversationReviewTask(
        task_id=selected_task_id,
        run_id=f"review_v2_{selected_task_id.hex}",
        owner_id=str(values["owner_id"]),
        idempotency_key=key,
        conversation_id=values["conversation_id"],  # type: ignore[arg-type]
        request_payload={"count": 5, "queue": 420, "focus": "overall"},
        created_at=NOW,
    )


def repository(engine: sa.Engine) -> PostgresTaskRepository:
    return PostgresTaskRepository(build_session_factory(engine))


def result_with_timeout(future: Future[object]) -> object:
    try:
        return future.result(timeout=10)
    except TimeoutError:
        pytest.fail("concurrent PostgreSQL Conversation Review operation timed out")


def test_atomic_create_persists_frozen_tuple_and_private_target(
    postgres_engine: sa.Engine,
) -> None:
    values = seed_conversation(postgres_engine)
    repo = repository(postgres_engine)

    result = repo.create_conversation_bound_or_replay(
        pending(values),
        capacity=TaskCapacityPolicy(),
    )

    assert result.disposition is TaskRepositoryCreateDisposition.CREATED
    assert result.task is not None
    task = result.task
    assert task.schema_version == "2.0"
    assert task.conversation_binding is not None
    assert task.conversation_binding.conversation_id == values["conversation_id"]
    assert task.conversation_binding.relationship_id == values["relationship_id"]
    assert task.conversation_binding.player_subject_id == values["player_subject_id"]
    assert task.execution_target is not None
    assert task.execution_target.puuid == values["puuid"]
    assert task.execution_target.game_name == "Initial Name"

    with build_session_factory(postgres_engine)() as session:
        record = session.get(ReviewTaskRecord, task.task_id)
        assert record is not None
        assert record.conversation_id == values["conversation_id"]
        assert record.relationship_id == values["relationship_id"]
        assert record.player_subject_id == values["player_subject_id"]
        assert record.relationship_role == "self"
        assert "puuid" not in record.request_payload


def test_replay_is_stable_but_same_key_in_another_conversation_conflicts(
    postgres_engine: sa.Engine,
) -> None:
    first = seed_conversation(postgres_engine)
    second = seed_conversation(postgres_engine)
    repo = repository(postgres_engine)
    original = pending(first, key="shared-key")

    created = repo.create_conversation_bound_or_replay(
        original,
        capacity=TaskCapacityPolicy(),
    )
    replayed = repo.create_conversation_bound_or_replay(
        pending(first, key="shared-key"),
        capacity=TaskCapacityPolicy(),
    )
    conflict = repo.create_conversation_bound_or_replay(
        pending(second, key="shared-key"),
        capacity=TaskCapacityPolicy(),
    )

    assert created.task is not None and replayed.task is not None
    assert replayed.disposition is TaskRepositoryCreateDisposition.REPLAYED
    assert replayed.task.task_id == created.task.task_id
    assert conflict.disposition is TaskRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT


def test_wrong_owner_archived_or_hidden_relationship_cannot_create(
    postgres_engine: sa.Engine,
) -> None:
    values = seed_conversation(postgres_engine)
    repo = repository(postgres_engine)

    wrong_owner = repo.create_conversation_bound_or_replay(
        pending({**values, "owner_id": "owner-other"}),
        capacity=TaskCapacityPolicy(),
    )
    with postgres_engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE conversations SET status='archived' "
                "WHERE conversation_id=:conversation_id"
            ),
            values,
        )
    archived = repo.create_conversation_bound_or_replay(
        pending(values, key="archived"),
        capacity=TaskCapacityPolicy(),
    )

    assert wrong_owner.disposition is TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE
    assert archived.disposition is TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE


def test_alias_rename_changes_display_only_and_late_claim_keeps_subject(
    postgres_engine: sa.Engine,
) -> None:
    values = seed_conversation(postgres_engine)
    repo = repository(postgres_engine)
    created = repo.create_conversation_bound_or_replay(
        pending(values),
        capacity=TaskCapacityPolicy(),
    )
    assert created.task is not None

    with postgres_engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO player_aliases (player_alias_id, player_subject_id, "
                "routing_region, game_name, tag_line, normalized_riot_id_hash, "
                "first_seen_at, last_seen_at) VALUES (:alias_id, :player_subject_id, "
                "'asia', 'Renamed Player', 'KR2', :alias_hash, "
                ":seen_at, :seen_at)"
            ),
            {
                **values,
                "alias_id": uuid4(),
                "alias_hash": uuid4().hex * 2,
                "seen_at": NOW.replace(hour=10),
            },
        )
        connection.execute(
            sa.text(
                "UPDATE conversations SET status='archived' "
                "WHERE conversation_id=:conversation_id"
            ),
            values,
        )

    claimed = repo.claim_next(worker_id="review-v2-worker", now=NOW.replace(hour=11))

    assert claimed is not None
    assert claimed.status is TaskStatus.RUNNING
    assert claimed.conversation_binding is not None
    assert claimed.conversation_binding.player_subject_id == values["player_subject_id"]
    assert claimed.execution_target is not None
    assert claimed.execution_target.puuid == values["puuid"]
    assert claimed.execution_target.game_name == "Renamed Player"
    assert claimed.execution_target.tag_line == "KR2"


def test_conversation_bound_create_enforces_capacity_and_rolls_back_bad_target(
    postgres_engine: sa.Engine,
) -> None:
    first = seed_conversation(postgres_engine)
    second = seed_conversation(postgres_engine)
    repo = repository(postgres_engine)

    created = repo.create_conversation_bound_or_replay(
        pending(first, key="capacity-first"),
        capacity=TaskCapacityPolicy(owner_active_limit=1, global_active_limit=2),
    )
    limited = repo.create_conversation_bound_or_replay(
        pending(second, key="capacity-second"),
        capacity=TaskCapacityPolicy(owner_active_limit=1, global_active_limit=2),
    )
    assert created.disposition is TaskRepositoryCreateDisposition.CREATED
    assert (
        limited.disposition
        is TaskRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED
    )

    third = seed_conversation(postgres_engine, owner_id="owner-bad-target")
    with postgres_engine.begin() as connection:
        connection.execute(
            sa.text(
                "DELETE FROM player_aliases "
                "WHERE player_subject_id=:player_subject_id"
            ),
            third,
        )
    with pytest.raises(TaskRepositoryError) as failure:
        repo.create_conversation_bound_or_replay(
            pending(third, key="bad-target"),
            capacity=TaskCapacityPolicy(),
        )
    assert failure.value.args == ("task_repository_integrity_failed",)
    with build_session_factory(postgres_engine)() as session:
        assert session.scalar(
            sa.select(sa.func.count())
            .select_from(ReviewTaskRecord)
            .where(ReviewTaskRecord.owner_id == "owner-bad-target")
        ) == 0


@pytest.mark.parametrize(
    "mutation_name",
    ("archive_conversation", "hide_conversation"),
    ids=("archive", "hide"),
)
@pytest.mark.parametrize(
    "create_first",
    (True, False),
    ids=("create-first", "lifecycle-first"),
)
def test_create_and_lifecycle_follow_relationship_then_conversation_lock_order(
    postgres_engine: sa.Engine,
    mutation_name: str,
    create_first: bool,
) -> None:
    values = seed_conversation(postgres_engine)
    factory = build_session_factory(postgres_engine)
    task_repository = PostgresTaskRepository(factory)
    conversation_repository = PostgresConversationRepository(factory)
    first_relationship_locked = Event()
    second_relationship_attempted = Event()
    first_thread_prefix = "conversation-review-lock-first"
    second_thread_prefix = "conversation-review-lock-second"

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

    def create_task():
        return task_repository.create_conversation_bound_or_replay(
            pending(values, key=f"lifecycle-{mutation_name}"),
            capacity=TaskCapacityPolicy(),
        )

    def mutate_conversation():
        mutation = getattr(conversation_repository, mutation_name)
        return mutation(
            owner_id=str(values["owner_id"]),
            conversation_id=values["conversation_id"],
            now=NOW.replace(hour=12),
        )

    first_operation = create_task if create_first else mutate_conversation
    second_operation = mutate_conversation if create_first else create_task
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
                ConversationRecord.conversation_id == values["conversation_id"]
            )
            .with_for_update()
        )
        sa.event.listen(
            postgres_engine,
            "after_cursor_execute",
            after_cursor_execute,
        )
        sa.event.listen(
            postgres_engine,
            "before_cursor_execute",
            before_cursor_execute,
        )
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
                postgres_engine,
                "after_cursor_execute",
                after_cursor_execute,
            )
            sa.event.remove(
                postgres_engine,
                "before_cursor_execute",
                before_cursor_execute,
            )
            first_executor.shutdown(wait=True, cancel_futures=True)
            second_executor.shutdown(wait=True, cancel_futures=True)

    create_result = first_result if create_first else second_result
    mutation_result = second_result if create_first else first_result
    assert (
        mutation_result.disposition
        is ConversationRepositoryMutationDisposition.UPDATED
    )
    expected_create = (
        TaskRepositoryCreateDisposition.CREATED
        if create_first
        else TaskRepositoryCreateDisposition.CONVERSATION_UNAVAILABLE
    )
    assert create_result.disposition is expected_create
    with factory() as session:
        assert session.scalar(
            sa.select(sa.func.count()).select_from(ReviewTaskRecord)
        ) == (1 if create_first else 0)
