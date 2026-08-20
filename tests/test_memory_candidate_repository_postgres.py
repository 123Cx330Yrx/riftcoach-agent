from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.memory.models import (
    CandidateCreateDisposition,
    CandidateMutationDisposition,
    CandidateStatus,
    MemoryConversationIdentity,
    RelationshipRole,
)
from app.persistence import memory_repository as repository_module
from app.persistence.memory_repository import PostgresMemoryCandidateRepository
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)


def test_memory_candidate_advisory_lock_is_scoped_and_stable() -> None:
    lock_id = getattr(repository_module, "_candidate_create_lock_id")
    first = lock_id("owner-1", "key-1")
    assert first == lock_id("owner-1", "key-1")
    assert first != lock_id("owner-1", "key-2")
    assert first != lock_id("owner-2", "key-1")
    assert -(2**63) <= first < 2**63


def test_create_derives_identity_and_is_owner_scoped() -> None:
    with migrated_memory_repository() as (repository, factory, _engine):
        subject_id, relationship_id, conversation_id = seed_conversation(factory)
        identity = repository.get_conversation_identity(
            owner_id="memory-owner", conversation_id=conversation_id
        )
        assert identity == MemoryConversationIdentity(
            owner_id="memory-owner",
            conversation_id=conversation_id,
            relationship_id=relationship_id,
            player_subject_id=subject_id,
            relationship_role=RelationshipRole.SELF,
        )
        assert repository.get_conversation_identity(
            owner_id="different-owner", conversation_id=conversation_id
        ) is None

        result = repository.create_or_replay_candidate(
            pending_candidate(1, conversation_id=conversation_id),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert result.disposition is CandidateCreateDisposition.CREATED
        assert result.candidate is not None
        assert result.candidate.player_subject_id == subject_id
        assert repository.get_candidate(
            owner_id="different-owner", candidate_id=result.candidate.candidate_id
        ) is None


def test_create_replays_same_fingerprint_and_conflicts_on_changed_payload() -> None:
    with migrated_memory_repository() as (repository, factory, _engine):
        _subject, _relationship, conversation_id = seed_conversation(factory)
        identity = repository.get_conversation_identity(
            owner_id="memory-owner", conversation_id=conversation_id
        )
        assert identity is not None
        original = pending_candidate(1, conversation_id=conversation_id, key="same-key")
        created = repository.create_or_replay_candidate(
            original,
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        replay = repository.create_or_replay_candidate(
            original.model_copy(update={"candidate_id": UUID("84000000-0000-4000-8000-000000000099")}),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        conflict = repository.create_or_replay_candidate(
            pending_candidate(
                2,
                conversation_id=conversation_id,
                key="same-key",
                payload={"value": "en-US"},
            ),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert created.disposition is CandidateCreateDisposition.CREATED
        assert replay.disposition is CandidateCreateDisposition.REPLAYED
        assert replay.candidate == created.candidate
        assert conflict.disposition is CandidateCreateDisposition.IDEMPOTENCY_CONFLICT


def test_reject_is_terminal_and_expiry_requires_due_time() -> None:
    with migrated_memory_repository() as (repository, factory, _engine):
        _subject, _relationship, conversation_id = seed_conversation(factory)
        identity = repository.get_conversation_identity(
            owner_id="memory-owner", conversation_id=conversation_id
        )
        assert identity is not None
        created = repository.create_or_replay_candidate(
            pending_candidate(1, conversation_id=conversation_id),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert created.candidate is not None
        not_due = repository.expire_candidate(
            owner_id="memory-owner",
            candidate_id=created.candidate.candidate_id,
            now=BASE + timedelta(days=1),
        )
        rejected = repository.reject_candidate(
            owner_id="memory-owner",
            candidate_id=created.candidate.candidate_id,
            actor_id="memory-owner",
            reason_code="user_rejected",
            now=BASE + timedelta(days=2),
        )
        replay = repository.reject_candidate(
            owner_id="memory-owner",
            candidate_id=created.candidate.candidate_id,
            actor_id="memory-owner",
            reason_code="user_rejected",
            now=BASE + timedelta(days=3),
        )
        assert not_due.disposition is CandidateMutationDisposition.TERMINAL_CONFLICT
        assert rejected.disposition is CandidateMutationDisposition.REJECTED
        assert rejected.candidate is not None
        assert rejected.candidate.status is CandidateStatus.REJECTED
        assert replay.disposition is CandidateMutationDisposition.REPLAYED


def test_accept_without_materializer_is_fail_closed_and_non_mutating() -> None:
    with migrated_memory_repository() as (repository, factory, _engine):
        _subject, _relationship, conversation_id = seed_conversation(factory)
        identity = repository.get_conversation_identity(
            owner_id="memory-owner", conversation_id=conversation_id
        )
        assert identity is not None
        created = repository.create_or_replay_candidate(
            pending_candidate(1, conversation_id=conversation_id),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert created.candidate is not None
        result = repository.accept_candidate(
            owner_id="memory-owner",
            candidate_id=created.candidate.candidate_id,
            actor_id="memory-owner",
            actor_kind=repository_module.DecisionActorKind.USER,
            now=BASE + timedelta(days=1),
            materializers={},
        )
        stored = repository.get_candidate(
            owner_id="memory-owner", candidate_id=created.candidate.candidate_id
        )
        assert result.disposition is CandidateMutationDisposition.TARGET_UNAVAILABLE
        assert stored is not None and stored.status is CandidateStatus.PENDING
