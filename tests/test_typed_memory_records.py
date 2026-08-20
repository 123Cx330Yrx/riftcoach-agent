from __future__ import annotations

from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)


def names(items) -> set[str]:
    return {item.name for item in items if item.name is not None}


def test_typed_memory_tables_have_expected_identity_columns() -> None:
    for record_type in (MemoryPreferenceRecord, PlayerProfileRecord, ReviewMemoryRecord):
        table = record_type.__table__
        assert {
            "record_id",
            "owner_id",
            "source_conversation_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            "memory_key",
            "version",
            "status",
            "payload",
            "payload_sha256",
            "source_candidate_id",
            "supersedes_record_id",
        } <= set(table.columns.keys())


def test_each_typed_table_has_source_candidate_and_active_uniqueness() -> None:
    expected = {
        MemoryPreferenceRecord: {
            "uq_memory_preferences_source_candidate",
            "uq_memory_preferences_version",
            "uq_memory_preferences_active",
        },
        PlayerProfileRecord: {
            "uq_player_profiles_source_candidate",
            "uq_player_profiles_version",
            "uq_player_profiles_active",
        },
        ReviewMemoryRecord: {
            "uq_review_memories_source_candidate",
            "uq_review_memories_version",
            "uq_review_memories_active",
        },
    }
    for record_type, required in expected.items():
        table = record_type.__table__
        actual = names(table.constraints) | names(table.indexes)
        assert required <= actual


def test_profile_and_review_tables_have_relationship_identity_fks() -> None:
    profile_fks = names(PlayerProfileRecord.__table__.foreign_key_constraints)
    review_fks = names(ReviewMemoryRecord.__table__.foreign_key_constraints)
    assert {
        "fk_player_profiles_candidate_identity",
        "fk_player_profiles_relationship_identity",
        "fk_player_profiles_supersedes",
    } <= profile_fks
    assert {
        "fk_review_memories_candidate_identity",
        "fk_review_memories_relationship_identity",
        "fk_review_memories_supersedes",
    } <= review_fks


def test_typed_tables_have_status_version_and_scope_checks() -> None:
    for record_type in (MemoryPreferenceRecord, PlayerProfileRecord, ReviewMemoryRecord):
        check_names = names(record_type.__table__.constraints)
        table_name = record_type.__tablename__
        assert {
            f"ck_{table_name}_status_allowed",
            f"ck_{table_name}_version_range",
            f"ck_{table_name}_supersedes_shape",
            f"ck_{table_name}_payload_digest_format",
        } <= check_names
    assert "ck_memory_preferences_self_only" in names(MemoryPreferenceRecord.__table__.constraints)
    assert "ck_player_profiles_self_only" in names(PlayerProfileRecord.__table__.constraints)
    assert "ck_review_memories_observed_key_allowed" in names(ReviewMemoryRecord.__table__.constraints)
