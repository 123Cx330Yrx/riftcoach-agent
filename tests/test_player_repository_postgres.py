from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from typing import TypeVar
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerAliasRecord,
    PlayerLinkTaskRecord,
    PlayerSubjectRecord,
)
from app.persistence.player_repository import (
    PostgresPlayerRepository,
    _record_to_link_task,
)
from app.players.models import (
    PendingPlayerLinkTask,
    PlayerLinkCapacityPolicy,
    PlayerLinkFailure,
    PlayerLinkRepositoryCreateDisposition,
    PlayerLinkStatus,
    PlayerLinkTaskView,
    RelationshipRole,
    ResolvedRiotAccount,
    RoutingRegion,
    VerificationStatus,
    compute_alias_hash,
)
from app.players.ports import PlayerRepositoryError


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"
BASE = datetime(2026, 8, 19, 8, 0, 0, tzinfo=timezone.utc)
T = TypeVar("T")


@contextmanager
def migrated_repository() -> Iterator[
    tuple[PostgresPlayerRepository, sessionmaker[Session], sa.Engine]
]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL player "
            "repository evidence runs in CI"
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
        yield PostgresPlayerRepository(factory), factory, engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def pending(
    number: int,
    *,
    owner_id: str = "owner-1",
    key: str | None = None,
    fingerprint: str | None = None,
    role: RelationshipRole = RelationshipRole.SELF,
    created_offset: int | None = None,
) -> PendingPlayerLinkTask:
    verification = (
        VerificationStatus.UNVERIFIED_CLAIM
        if role is RelationshipRole.SELF
        else VerificationStatus.NOT_APPLICABLE
    )
    game_name = f"DemoPlayer{number}"
    tag_line = "TEST"
    return PendingPlayerLinkTask(
        link_task_id=UUID(f"60000000-0000-4000-8000-{number:012d}"),
        owner_id=owner_id,
        idempotency_key=key or f"player-link-{number}",
        request_fingerprint=fingerprint or f"{number:064x}",
        routing_region=RoutingRegion.ASIA,
        relationship_role=role,
        verification_status=verification,
        game_name=game_name,
        tag_line=tag_line,
        alias_hash=compute_alias_hash(game_name=game_name, tag_line=tag_line),
        created_at=BASE + timedelta(seconds=created_offset or number),
    )


def resolved(
    *,
    puuid: str = "PUUID_DEMO_1234567890",
    game_name: str = "ConfirmedPlayer",
    tag_line: str = "KR1",
) -> ResolvedRiotAccount:
    return ResolvedRiotAccount(
        routing_region=RoutingRegion.ASIA,
        puuid=puuid,
        game_name=game_name,
        tag_line=tag_line,
    )


def create(
    repository: PostgresPlayerRepository,
    *tasks: PendingPlayerLinkTask,
) -> None:
    for task in tasks:
        result = repository.create_or_replay_link(
            task,
            capacity=PlayerLinkCapacityPolicy(
                owner_active_limit=20,
                global_active_limit=100,
            ),
        )
        assert (
            result.disposition
            is PlayerLinkRepositoryCreateDisposition.CREATED
        )


def claim(
    repository: PostgresPlayerRepository,
    *,
    worker_id: str,
    now: datetime = BASE + timedelta(minutes=1),
):
    task = repository.claim_next_link(worker_id=worker_id, now=now)
    assert task is not None
    return task


def _result_with_timeout(future: Future[T]) -> T:
    try:
        return future.result(timeout=8)
    except TimeoutError:
        pytest.fail("concurrent PostgreSQL player repository operation timed out")


def test_record_mapping_is_strict_and_keeps_private_request_fields() -> None:
    source = pending(1)
    record = PlayerLinkTaskRecord(
        link_task_id=source.link_task_id,
        task_kind=source.task_kind,
        schema_version=source.schema_version,
        owner_id=source.owner_id,
        worker_id=None,
        idempotency_key=source.idempotency_key,
        request_fingerprint=source.request_fingerprint,
        game_name=source.game_name,
        tag_line=source.tag_line,
        routing_region=source.routing_region.value,
        relationship_role=source.relationship_role.value,
        alias_hash=source.alias_hash,
        status=PlayerLinkStatus.QUEUED.value,
        created_at=source.created_at,
        updated_at=source.created_at,
        claimed_at=None,
        finished_at=None,
        terminal_reason=None,
        confirmed_game_name=None,
        confirmed_tag_line=None,
        player_subject_id=None,
        relationship_id=None,
    )

    task = _record_to_link_task(record, relationship=None)

    assert task.status is PlayerLinkStatus.QUEUED
    assert task.game_name == source.game_name
    assert task.tag_line == source.tag_line
    assert task.verification_status is VerificationStatus.UNVERIFIED_CLAIM
    public_view = PlayerLinkTaskView.from_task(task)
    assert "game_name" not in public_view.model_dump(mode="json")
    assert "tag_line" not in public_view.model_dump(mode="json")


def test_create_replay_conflict_capacity_and_owner_scope() -> None:
    policy = PlayerLinkCapacityPolicy(owner_active_limit=1, global_active_limit=2)
    with migrated_repository() as (repository, factory, _engine):
        original = pending(1, key="same", fingerprint="a" * 64)
        alternate = pending(2, key="same", fingerprint="a" * 64)

        created = repository.create_or_replay_link(original, capacity=policy)
        replayed = repository.create_or_replay_link(alternate, capacity=policy)
        conflict = repository.create_or_replay_link(
            pending(3, key="same", fingerprint="b" * 64),
            capacity=policy,
        )
        owner_full = repository.create_or_replay_link(
            pending(4, key="owner-full"),
            capacity=policy,
        )
        other_owner = repository.create_or_replay_link(
            pending(5, owner_id="owner-2"),
            capacity=policy,
        )
        global_full = repository.create_or_replay_link(
            pending(6, owner_id="owner-3"),
            capacity=policy,
        )

        assert created.disposition is PlayerLinkRepositoryCreateDisposition.CREATED
        assert replayed.disposition is PlayerLinkRepositoryCreateDisposition.REPLAYED
        assert replayed.task is not None
        assert replayed.task.link_task_id == original.link_task_id
        assert (
            conflict.disposition
            is PlayerLinkRepositoryCreateDisposition.IDEMPOTENCY_CONFLICT
        )
        assert (
            owner_full.disposition
            is PlayerLinkRepositoryCreateDisposition.OWNER_CAPACITY_EXCEEDED
        )
        assert other_owner.disposition is PlayerLinkRepositoryCreateDisposition.CREATED
        assert (
            global_full.disposition
            is PlayerLinkRepositoryCreateDisposition.GLOBAL_CAPACITY_EXCEEDED
        )
        assert repository.get_link_by_id(
            owner_id="owner-1", link_task_id=original.link_task_id
        ) is not None
        assert repository.get_link_by_id(
            owner_id="owner-2", link_task_id=original.link_task_id
        ) is None
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(PlayerLinkTaskRecord)
            ) == 2


def test_claim_is_deterministic_and_commits_private_riot_id_round_trip() -> None:
    with migrated_repository() as (repository, factory, _engine):
        high_id = pending(3, created_offset=1)
        first = pending(1, created_offset=1)
        later = pending(2, created_offset=2)
        create(repository, high_id, later, first)

        claimed = [
            repository.claim_next_link(
                worker_id=f"worker-{number}",
                now=BASE + timedelta(minutes=number),
            )
            for number in range(1, 4)
        ]
        assert [task.link_task_id for task in claimed if task is not None] == [
            first.link_task_id,
            high_id.link_task_id,
            later.link_task_id,
        ]
        assert claimed[0] is not None
        assert claimed[0].game_name == first.game_name
        assert claimed[0].tag_line == first.tag_line
        assert "game_name" not in PlayerLinkTaskView.from_task(claimed[0]).model_dump(
            mode="json"
        )

        with factory.begin() as session:
            record = session.scalar(
                sa.select(PlayerLinkTaskRecord)
                .where(PlayerLinkTaskRecord.link_task_id == first.link_task_id)
                .with_for_update(nowait=True)
            )
            assert record is not None
            assert record.status == PlayerLinkStatus.RUNNING.value


def test_two_workers_cannot_claim_the_same_link_task() -> None:
    with migrated_repository() as (repository, _factory, _engine):
        task = pending(1)
        create(repository, task)
        barrier = Barrier(2)

        def run(worker_id: str):
            barrier.wait(timeout=5)
            return repository.claim_next_link(
                worker_id=worker_id,
                now=BASE + timedelta(minutes=1),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run, worker) for worker in ("w-1", "w-2")]
            results = [_result_with_timeout(future) for future in futures]

        claimed = [result for result in results if result is not None]
        assert len(claimed) == 1
        assert claimed[0].link_task_id == task.link_task_id


def test_resolve_atomically_creates_identity_and_confirmed_display_snapshot() -> None:
    with migrated_repository() as (repository, factory, _engine):
        task = pending(1)
        create(repository, task)
        claim(repository, worker_id="worker-1")

        terminal = repository.resolve_link(
            link_task_id=task.link_task_id,
            worker_id="worker-1",
            resolved_account=resolved(),
        )

        assert terminal is not None
        assert terminal.status is PlayerLinkStatus.SUCCEEDED
        assert terminal.confirmed_game_name == "ConfirmedPlayer"
        assert terminal.confirmed_tag_line == "KR1"
        assert terminal.relationship is not None
        assert terminal.relationship.relationship_role is RelationshipRole.SELF
        assert (
            terminal.relationship.verification_status
            is VerificationStatus.UNVERIFIED_CLAIM
        )
        public_view = PlayerLinkTaskView.from_task(terminal)
        assert public_view.confirmed_riot_id == "ConfirmedPlayer#KR1"
        assert "puuid" not in public_view.model_dump_json().lower()

        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(PlayerSubjectRecord)
            ) == 1
            assert session.scalar(
                sa.select(sa.func.count()).select_from(PlayerAliasRecord)
            ) == 1
            assert session.scalar(
                sa.select(sa.func.count()).select_from(
                    OwnerPlayerRelationshipRecord
                )
            ) == 1


def test_concurrent_same_puuid_resolutions_converge() -> None:
    with migrated_repository() as (repository, factory, _engine):
        tasks = (pending(1, owner_id="owner-1"), pending(2, owner_id="owner-2"))
        create(repository, *tasks)
        claim(repository, worker_id="worker-1")
        claim(repository, worker_id="worker-2")
        barrier = Barrier(2)

        def run(task: PendingPlayerLinkTask, worker_id: str):
            barrier.wait(timeout=5)
            return repository.resolve_link(
                link_task_id=task.link_task_id,
                worker_id=worker_id,
                resolved_account=resolved(),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(run, tasks[0], "worker-1"),
                executor.submit(run, tasks[1], "worker-2"),
            ]
            results = [_result_with_timeout(future) for future in futures]

        assert all(result is not None for result in results)
        assert {result.status for result in results if result is not None} == {
            PlayerLinkStatus.SUCCEEDED
        }
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(PlayerSubjectRecord)
            ) == 1
            assert session.scalar(
                sa.select(sa.func.count()).select_from(PlayerAliasRecord)
            ) == 1
            assert session.scalar(
                sa.select(sa.func.count()).select_from(
                    OwnerPlayerRelationshipRecord
                )
            ) == 2


def test_same_owner_subject_role_reuses_relationship() -> None:
    with migrated_repository() as (repository, factory, _engine):
        first = pending(1, owner_id="owner-1")
        second = pending(2, owner_id="owner-1")
        create(repository, first)
        claim(repository, worker_id="worker-1")
        first_terminal = repository.resolve_link(
            link_task_id=first.link_task_id,
            worker_id="worker-1",
            resolved_account=resolved(),
        )
        create(repository, second)
        claim(repository, worker_id="worker-2")
        second_terminal = repository.resolve_link(
            link_task_id=second.link_task_id,
            worker_id="worker-2",
            resolved_account=resolved(),
        )

        assert first_terminal is not None and first_terminal.relationship is not None
        assert second_terminal is not None and second_terminal.relationship is not None
        assert (
            first_terminal.relationship.relationship_id
            == second_terminal.relationship.relationship_id
        )
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(
                    OwnerPlayerRelationshipRecord
                )
            ) == 1


def test_profile_list_is_owner_scoped_latest_success_only_and_hidden_safe() -> None:
    with migrated_repository() as (repository, factory, _engine):
        first = pending(1, owner_id="owner-1")
        create(repository, first)
        claim(repository, worker_id="worker-1")
        first_terminal = repository.resolve_link(
            link_task_id=first.link_task_id,
            worker_id="worker-1",
            resolved_account=resolved(game_name="Old Name", tag_line="KR1"),
        )
        assert first_terminal is not None and first_terminal.relationship is not None

        duplicate = pending(2, owner_id="owner-1")
        create(repository, duplicate)
        claim(repository, worker_id="worker-2")
        duplicate_terminal = repository.resolve_link(
            link_task_id=duplicate.link_task_id,
            worker_id="worker-2",
            resolved_account=resolved(game_name="New Name", tag_line="KR2"),
        )
        assert duplicate_terminal is not None

        other = pending(4, owner_id="owner-2", role=RelationshipRole.OBSERVED)
        create(repository, other)
        claim(repository, worker_id="worker-3")
        other_terminal = repository.resolve_link(
            link_task_id=other.link_task_id,
            worker_id="worker-3",
            resolved_account=resolved(
                puuid="PUUID_OTHER_1234567890",
                game_name="Observed Pro",
                tag_line="EUW",
            ),
        )
        assert other_terminal is not None
        create(repository, pending(3, owner_id="owner-1"))

        owner_profiles = repository.list_profiles(owner_id="owner-1", limit=50)
        other_profiles = repository.list_profiles(owner_id="owner-2", limit=50)

        assert len(owner_profiles) == 1
        assert owner_profiles[0].riot_id == "New Name#KR2"
        assert (
            owner_profiles[0].player_profile_id
            == first_terminal.relationship.relationship_id
        )
        assert len(other_profiles) == 1
        assert other_profiles[0].relationship_role is RelationshipRole.OBSERVED
        assert (
            other_profiles[0].verification_status
            is VerificationStatus.NOT_APPLICABLE
        )
        assert "puuid" not in owner_profiles[0].model_dump_json().lower()

        with factory.begin() as session:
            relationship = session.get(
                OwnerPlayerRelationshipRecord,
                first_terminal.relationship.relationship_id,
            )
            assert relationship is not None
            relationship.status = "hidden"
            relationship.hidden_at = relationship.created_at + timedelta(minutes=1)
            relationship.updated_at = relationship.hidden_at

        assert repository.list_profiles(owner_id="owner-1", limit=50) == ()


def test_role_conflict_is_one_transaction_failure_without_alias_mutation() -> None:
    with migrated_repository() as (repository, factory, _engine):
        first = pending(1, role=RelationshipRole.SELF)
        create(repository, first)
        claim(repository, worker_id="worker-1")
        assert repository.resolve_link(
            link_task_id=first.link_task_id,
            worker_id="worker-1",
            resolved_account=resolved(),
        ) is not None

        with factory() as session:
            alias_before = session.scalar(
                sa.select(sa.func.count()).select_from(PlayerAliasRecord)
            )

        conflicting = pending(2, role=RelationshipRole.OBSERVED)
        create(repository, conflicting)
        claim(repository, worker_id="worker-2")
        terminal = repository.resolve_link(
            link_task_id=conflicting.link_task_id,
            worker_id="worker-2",
            resolved_account=resolved(),
        )

        assert terminal is not None
        assert terminal.status is PlayerLinkStatus.FAILED
        assert terminal.failure is not None
        assert terminal.failure.code == "relationship_role_conflict"
        assert terminal.subject_id is None
        assert terminal.relationship is None
        with factory() as session:
            assert session.scalar(
                sa.select(sa.func.count()).select_from(PlayerAliasRecord)
            ) == alias_before
            relationships = tuple(
                session.scalars(sa.select(OwnerPlayerRelationshipRecord))
            )
            assert len(relationships) == 1
            assert relationships[0].relationship_role == RelationshipRole.SELF.value


def test_stale_worker_terminal_cas_and_failure_are_irreversible() -> None:
    with migrated_repository() as (repository, _factory, _engine):
        task = pending(1)
        create(repository, task)
        claim(repository, worker_id="worker-1")

        assert repository.resolve_link(
            link_task_id=task.link_task_id,
            worker_id="worker-2",
            resolved_account=resolved(),
        ) is None
        assert repository.fail_link(
            link_task_id=task.link_task_id,
            worker_id="worker-2",
            failure=PlayerLinkFailure(code="upstream_timeout", retryable=True),
        ) is None
        failed = repository.fail_link(
            link_task_id=task.link_task_id,
            worker_id="worker-1",
            failure=PlayerLinkFailure(code="upstream_timeout", retryable=True),
        )
        assert failed is not None
        assert failed.status is PlayerLinkStatus.FAILED
        assert failed.subject_id is None
        assert failed.relationship is None
        assert repository.fail_link(
            link_task_id=task.link_task_id,
            worker_id="worker-1",
            failure=PlayerLinkFailure(code="upstream_timeout", retryable=True),
        ) is None
        assert repository.resolve_link(
            link_task_id=task.link_task_id,
            worker_id="worker-1",
            resolved_account=resolved(),
        ) is None


def test_resolution_sql_error_rolls_back_all_identity_writes() -> None:
    with migrated_repository() as (repository, factory, engine):
        task = pending(1)
        create(repository, task)
        claim(repository, worker_id="worker-1")

        def fail_alias_insert(
            _conn, _cursor, statement, _parameters, _context, _executemany
        ) -> None:
            if statement.lstrip().startswith("INSERT INTO player_aliases"):
                raise sa.exc.OperationalError(
                    statement,
                    {},
                    RuntimeError("injected alias failure"),
                )

        event.listen(engine, "before_cursor_execute", fail_alias_insert)
        try:
            with pytest.raises(PlayerRepositoryError):
                repository.resolve_link(
                    link_task_id=task.link_task_id,
                    worker_id="worker-1",
                    resolved_account=resolved(),
                )
        finally:
            event.remove(engine, "before_cursor_execute", fail_alias_insert)

        current = repository.get_link_by_id(
            owner_id=task.owner_id,
            link_task_id=task.link_task_id,
        )
        assert current is not None
        assert current.status is PlayerLinkStatus.RUNNING
        with factory() as session:
            for model in (
                PlayerSubjectRecord,
                PlayerAliasRecord,
                OwnerPlayerRelationshipRecord,
            ):
                assert session.scalar(
                    sa.select(sa.func.count()).select_from(model)
                ) == 0


def test_terminal_time_is_timezone_aware_and_monotonic() -> None:
    with migrated_repository() as (repository, _factory, _engine):
        task = pending(1)
        create(repository, task)
        future_claim = datetime.now(timezone.utc) + timedelta(days=1)
        claim(repository, worker_id="worker-1", now=future_claim)
        terminal = repository.resolve_link(
            link_task_id=task.link_task_id,
            worker_id="worker-1",
            resolved_account=resolved(),
        )

        assert terminal is not None
        assert terminal.created_at.utcoffset() == timedelta(0)
        assert terminal.claimed_at == future_claim
        assert terminal.finished_at is not None
        assert terminal.finished_at >= future_claim
        assert terminal.updated_at >= terminal.finished_at
