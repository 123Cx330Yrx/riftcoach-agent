from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Lock
from uuid import UUID

import pytest
import sqlalchemy as sa

from app.memory.models import (
    CandidateKind,
    CandidateMutationDisposition,
    CandidateStatus,
    DecisionActorKind,
    MaterializedMemoryReference,
)
from app.memory.ports import MaterializationSession
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from app.persistence.memory_records import MemoryCandidateRecord
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)


TARGET_ID = UUID("85000000-0000-4000-8000-000000000001")


class PreferenceTestMaterializer:
    candidate_kind = CandidateKind.OWNER_PREFERENCE
    version = "test-preference-v1"

    def __init__(self, *, fail_after_insert: bool = False) -> None:
        self.fail_after_insert = fail_after_insert
        self.calls = 0
        self._lock = Lock()

    def materialize(self, session: MaterializationSession, candidate):
        assert not hasattr(session, "commit")
        with self._lock:
            self.calls += 1
        session.execute(
            sa.text(
                "INSERT INTO test_memory_targets (target_id, source_candidate_id) "
                "VALUES (:target_id, :candidate_id)"
            ),
            {"target_id": TARGET_ID, "candidate_id": candidate.candidate_id},
        )
        if self.fail_after_insert:
            raise RuntimeError("test materializer failed")
        return MaterializedMemoryReference(
            target_kind="owner_preference",
            target_id=TARGET_ID,
            materializer_version=self.version,
        )


def _prepare(repository, factory, engine):
    _subject, _relationship, conversation_id = seed_conversation(factory)
    identity = repository.get_conversation_identity(
        owner_id="memory-owner", conversation_id=conversation_id
    )
    assert identity is not None
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE test_memory_targets ("
                "target_id UUID PRIMARY KEY, "
                "source_candidate_id UUID NOT NULL UNIQUE REFERENCES memory_candidates(candidate_id)"
                ")"
            )
        )
    created = repository.create_or_replay_candidate(
        pending_candidate(1, conversation_id=conversation_id),
        identity=identity,
        requires_confirmation=False,
        gate_policy_version="memory-gate-v1",
    )
    assert created.candidate is not None
    return created.candidate


def test_materializer_and_accepted_candidate_commit_once() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        candidate = _prepare(repository, factory, engine)
        materializer = PreferenceTestMaterializer()
        accepted = repository.accept_candidate(
            owner_id="memory-owner",
            candidate_id=candidate.candidate_id,
            actor_id="memory-owner",
            actor_kind=DecisionActorKind.USER,
            now=BASE + timedelta(days=1),
            materializers={CandidateKind.OWNER_PREFERENCE: materializer},
        )
        replay = repository.accept_candidate(
            owner_id="memory-owner",
            candidate_id=candidate.candidate_id,
            actor_id="memory-owner",
            actor_kind=DecisionActorKind.USER,
            now=BASE + timedelta(days=2),
            materializers={CandidateKind.OWNER_PREFERENCE: materializer},
        )
        with engine.connect() as connection:
            count = connection.scalar(sa.text("SELECT count(*) FROM test_memory_targets"))
        assert accepted.disposition is CandidateMutationDisposition.ACCEPTED
        assert accepted.candidate is not None
        assert accepted.candidate.status is CandidateStatus.ACCEPTED
        assert replay.disposition is CandidateMutationDisposition.REPLAYED
        assert materializer.calls == 1
        assert count == 1


def test_materializer_failure_rolls_back_target_and_candidate_terminal() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        candidate = _prepare(repository, factory, engine)
        materializer = PreferenceTestMaterializer(fail_after_insert=True)
        with pytest.raises(Exception, match="memory_candidate_materializer_failed"):
            repository.accept_candidate(
                owner_id="memory-owner",
                candidate_id=candidate.candidate_id,
                actor_id="memory-owner",
                actor_kind=DecisionActorKind.USER,
                now=BASE + timedelta(days=1),
                materializers={CandidateKind.OWNER_PREFERENCE: materializer},
            )
        stored = repository.get_candidate(
            owner_id="memory-owner", candidate_id=candidate.candidate_id
        )
        with engine.connect() as connection:
            count = connection.scalar(sa.text("SELECT count(*) FROM test_memory_targets"))
        assert stored is not None and stored.status is CandidateStatus.PENDING
        assert count == 0


def test_two_concurrent_accepts_call_materializer_once() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        candidate = _prepare(repository, factory, engine)
        materializer = PreferenceTestMaterializer()
        start = Barrier(2)

        def accept_once():
            start.wait(timeout=5)
            local = PostgresMemoryCandidateRepository(factory)
            return local.accept_candidate(
                owner_id="memory-owner",
                candidate_id=candidate.candidate_id,
                actor_id="memory-owner",
                actor_kind=DecisionActorKind.USER,
                now=BASE + timedelta(days=1),
                materializers={CandidateKind.OWNER_PREFERENCE: materializer},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(lambda _: accept_once(), range(2)))
        assert {item.disposition for item in results} == {
            CandidateMutationDisposition.ACCEPTED,
            CandidateMutationDisposition.REPLAYED,
        }
        assert materializer.calls == 1
