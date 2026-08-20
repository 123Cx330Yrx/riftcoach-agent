from __future__ import annotations

from datetime import timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError

from app.memory.models import CandidateCreateDisposition
from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)


def test_memory_candidate_migration_exposes_stable_constraints_and_indexes() -> None:
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        assert "memory_candidates" in inspector.get_table_names()
        assert {
            "uq_memory_candidates_owner_id_idempotency_key",
            "uq_memory_candidates_identity",
        } <= {item["name"] for item in inspector.get_unique_constraints("memory_candidates")}
        assert {
            "fk_memory_candidates_conversation_identity",
            "fk_memory_candidates_source_message",
            "fk_memory_candidates_source_task",
        } == {item["name"] for item in inspector.get_foreign_keys("memory_candidates")}
        assert {
            "ck_memory_candidates_status_shape",
            "ck_memory_candidates_timestamp_order",
            "ck_memory_candidates_confidence_range",
        } <= {item["name"] for item in inspector.get_check_constraints("memory_candidates")}
        assert {
            "ix_memory_candidates_owner_pending",
            "ix_memory_candidates_conversation_history",
            "ix_memory_candidates_expiry",
        } <= {item["name"] for item in inspector.get_indexes("memory_candidates")}


def test_direct_sql_cannot_mutate_proposal_or_reverse_terminal_state() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
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
        assert created.disposition is CandidateCreateDisposition.CREATED
        assert created.candidate is not None
        candidate_id = created.candidate.candidate_id

        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE memory_candidates SET memory_key = 'tampered' "
                        "WHERE candidate_id = :candidate_id"
                    ),
                    {"candidate_id": candidate_id},
                )

        repository.reject_candidate(
            owner_id="memory-owner",
            candidate_id=candidate_id,
            actor_id="memory-owner",
            reason_code="user_rejected",
            now=BASE + timedelta(days=1),
        )
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE memory_candidates SET status = 'pending', "
                        "decision_actor_kind = NULL, decision_actor_id = NULL, "
                        "decision_reason_code = NULL, decided_at = NULL "
                        "WHERE candidate_id = :candidate_id"
                    ),
                    {"candidate_id": candidate_id},
                )


def test_status_shape_rejects_accepted_without_materialization_reference() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
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
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE memory_candidates SET status = 'accepted', "
                        "decision_actor_kind = 'user', decision_actor_id = 'memory-owner', "
                        "decision_reason_code = 'user_confirmed', decided_at = :now, updated_at = :now "
                        "WHERE candidate_id = :candidate_id"
                    ),
                    {"candidate_id": created.candidate.candidate_id, "now": BASE + timedelta(days=1)},
                )
