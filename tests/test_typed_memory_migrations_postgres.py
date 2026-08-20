from __future__ import annotations

from datetime import timedelta

import sqlalchemy as sa
import pytest
from sqlalchemy.exc import DBAPIError

from tests.memory_candidate_postgres_support import (
    BASE,
    migrated_memory_repository,
    pending_candidate,
    seed_conversation,
)


def names(items) -> set[str]:
    return {item["name"] for item in items if item.get("name") is not None}


def insert_preference(
    connection,
    *,
    item,
    record_id: str,
    version: int = 1,
    supersedes_record_id: str | None = None,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO memory_preferences ("
            "record_id, schema_version, owner_id, source_conversation_id, "
            "relationship_id, player_subject_id, relationship_role, memory_key, "
            "version, status, payload, payload_sha256, source_candidate_id, "
            "supersedes_record_id, created_at, updated_at) VALUES ("
            ":record_id, '1.0', :owner_id, :conversation_id, :relationship_id, "
            ":subject_id, 'self', 'report_language', :version, 'active', "
            "CAST(:payload AS jsonb), :digest, :candidate_id, :supersedes, :now, :now)"
        ),
        {
            "record_id": record_id,
            "owner_id": item.owner_id,
            "conversation_id": item.conversation_id,
            "relationship_id": item.relationship_id,
            "subject_id": item.player_subject_id,
            "version": version,
            "payload": '{"value":"zh-CN"}',
            "digest": "4" * 64,
            "candidate_id": item.candidate_id,
            "supersedes": supersedes_record_id,
            "now": BASE,
        },
    )


def test_typed_memory_migration_exposes_three_constrained_tables() -> None:
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        assert {"memory_preferences", "player_profiles", "review_memories"} <= set(
            inspector.get_table_names()
        )

        assert {
            "uq_memory_preferences_source_candidate",
            "uq_memory_preferences_version",
        } <= names(inspector.get_unique_constraints("memory_preferences"))
        assert {
            "uq_player_profiles_source_candidate",
            "uq_player_profiles_version",
        } <= names(inspector.get_unique_constraints("player_profiles"))
        assert {
            "uq_review_memories_source_candidate",
            "uq_review_memories_version",
        } <= names(inspector.get_unique_constraints("review_memories"))


def test_typed_memory_migration_exposes_active_indexes_and_identity_fks() -> None:
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        assert "uq_memory_preferences_active" in names(
            inspector.get_indexes("memory_preferences")
        )
        assert "uq_player_profiles_active" in names(inspector.get_indexes("player_profiles"))
        assert "uq_review_memories_active" in names(inspector.get_indexes("review_memories"))
        assert {
            "fk_memory_preferences_candidate_identity",
            "fk_memory_preferences_supersedes",
        } <= names(inspector.get_foreign_keys("memory_preferences"))
        assert {
            "fk_player_profiles_candidate_identity",
            "fk_player_profiles_relationship_identity",
            "fk_player_profiles_supersedes",
        } <= names(inspector.get_foreign_keys("player_profiles"))
        assert {
            "fk_review_memories_candidate_identity",
            "fk_review_memories_relationship_identity",
            "fk_review_memories_supersedes",
        } <= names(inspector.get_foreign_keys("review_memories"))


def test_typed_memory_migration_exposes_role_version_and_payload_checks() -> None:
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        assert {
            "ck_memory_preferences_self_only",
            "ck_memory_preferences_supersedes_shape",
            "ck_memory_preferences_payload_storage_bound",
        } <= names(inspector.get_check_constraints("memory_preferences"))
        assert {
            "ck_player_profiles_self_only",
            "ck_player_profiles_version_range",
        } <= names(inspector.get_check_constraints("player_profiles"))
        assert {
            "ck_review_memories_observed_key_allowed",
            "ck_review_memories_version_range",
        } <= names(inspector.get_check_constraints("review_memories"))


def test_direct_sql_source_mismatch_and_payload_mutation_are_blocked() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        _subject, _relationship, conversation_id = seed_conversation(factory)
        identity = repository.get_conversation_identity(
            owner_id="memory-owner",
            conversation_id=conversation_id,
        )
        assert identity is not None
        created = repository.create_or_replay_candidate(
            pending_candidate(1, conversation_id=conversation_id),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert created.candidate is not None
        item = created.candidate
        record_id = "95000000-0000-4000-8000-000000000001"

        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "INSERT INTO player_profiles ("
                        "record_id, schema_version, owner_id, source_conversation_id, "
                        "relationship_id, player_subject_id, relationship_role, memory_key, "
                        "version, status, payload, payload_sha256, source_candidate_id, "
                        "supersedes_record_id, created_at, updated_at) VALUES ("
                        ":record_id, '1.0', :owner_id, :conversation_id, :relationship_id, "
                        ":subject_id, 'self', 'main_role', 1, 'active', "
                        "CAST(:payload AS jsonb), :digest, :candidate_id, NULL, :now, :now)"
                    ),
                    {
                        "record_id": record_id,
                        "owner_id": item.owner_id,
                        "conversation_id": item.conversation_id,
                        "relationship_id": item.relationship_id,
                        "subject_id": item.player_subject_id,
                        "payload": '{"value":"TOP"}',
                        "digest": "3" * 64,
                        "candidate_id": item.candidate_id,
                        "now": BASE,
                    },
                )

        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO memory_preferences ("
                    "record_id, schema_version, owner_id, source_conversation_id, "
                    "relationship_id, player_subject_id, relationship_role, memory_key, "
                    "version, status, payload, payload_sha256, source_candidate_id, "
                    "supersedes_record_id, created_at, updated_at) VALUES ("
                    ":record_id, '1.0', :owner_id, :conversation_id, :relationship_id, "
                    ":subject_id, 'self', 'report_language', 1, 'active', "
                    "CAST(:payload AS jsonb), :digest, :candidate_id, NULL, :now, :now)"
                ),
                {
                    "record_id": record_id,
                    "owner_id": item.owner_id,
                    "conversation_id": item.conversation_id,
                    "relationship_id": item.relationship_id,
                    "subject_id": item.player_subject_id,
                    "payload": '{"value":"zh-CN"}',
                    "digest": "4" * 64,
                    "candidate_id": item.candidate_id,
                    "now": BASE,
                },
            )
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE memory_preferences SET payload = CAST(:payload AS jsonb) "
                        "WHERE record_id = :record_id"
                    ),
                    {"record_id": record_id, "payload": '{"value":"en-US"}'},
                )


def test_direct_sql_rejects_terminal_candidate_as_materialization_source() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        _subject, _relationship, conversation_id = seed_conversation(factory)
        identity = repository.get_conversation_identity(
            owner_id="memory-owner",
            conversation_id=conversation_id,
        )
        assert identity is not None
        created = repository.create_or_replay_candidate(
            pending_candidate(1, conversation_id=conversation_id),
            identity=identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert created.candidate is not None
        repository.reject_candidate(
            owner_id="memory-owner",
            candidate_id=created.candidate.candidate_id,
            actor_id="memory-owner",
            reason_code="user_rejected",
            now=BASE + timedelta(days=2),
        )

        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                insert_preference(
                    connection,
                    item=created.candidate,
                    record_id="95000000-0000-4000-8000-000000000002",
                )


def test_direct_sql_rejects_non_contiguous_supersedes_chain() -> None:
    with migrated_memory_repository() as (repository, factory, engine):
        _subject, _relationship, first_conversation = seed_conversation(
            factory,
            number=1,
        )
        first_identity = repository.get_conversation_identity(
            owner_id="memory-owner",
            conversation_id=first_conversation,
        )
        assert first_identity is not None
        first_created = repository.create_or_replay_candidate(
            pending_candidate(1, conversation_id=first_conversation),
            identity=first_identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert first_created.candidate is not None
        first_record_id = "95000000-0000-4000-8000-000000000003"
        with engine.begin() as connection:
            insert_preference(
                connection,
                item=first_created.candidate,
                record_id=first_record_id,
            )
            connection.execute(
                sa.text(
                    "UPDATE memory_preferences SET status = 'superseded' "
                    "WHERE record_id = :record_id"
                ),
                {"record_id": first_record_id},
            )

        _subject, _relationship, second_conversation = seed_conversation(
            factory,
            number=2,
        )
        second_identity = repository.get_conversation_identity(
            owner_id="memory-owner",
            conversation_id=second_conversation,
        )
        assert second_identity is not None
        second_created = repository.create_or_replay_candidate(
            pending_candidate(2, conversation_id=second_conversation),
            identity=second_identity,
            requires_confirmation=False,
            gate_policy_version="memory-gate-v1",
        )
        assert second_created.candidate is not None

        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                insert_preference(
                    connection,
                    item=second_created.candidate,
                    record_id="95000000-0000-4000-8000-000000000004",
                    version=3,
                    supersedes_record_id=first_record_id,
                )
