from app.persistence.memory_records import MemoryCandidateRecord
from app.persistence.owner_data_lifecycle_records import OwnerDataDeletionRecord
from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord
from app.persistence.typed_memory_records import (
    MemoryPreferenceRecord,
    PlayerProfileRecord,
    ReviewMemoryRecord,
)


def test_private_memory_tables_expose_hidden_at() -> None:
    for record_type in (
        MemoryCandidateRecord,
        MemoryPreferenceRecord,
        PlayerProfileRecord,
        ReviewMemoryRecord,
        TrainingPlanRecord,
        TrainingProgressRecord,
    ):
        assert "hidden_at" in record_type.__table__.columns


def test_active_unique_indexes_exclude_hidden_rows() -> None:
    for record_type, index_name in (
        (MemoryPreferenceRecord, "uq_memory_preferences_active"),
        (PlayerProfileRecord, "uq_player_profiles_active"),
        (ReviewMemoryRecord, "uq_review_memories_active"),
        (TrainingPlanRecord, "uq_training_plans_active_relationship"),
    ):
        index = next(
            value for value in record_type.__table__.indexes if value.name == index_name
        )
        predicate = str(index.dialect_options["postgresql"]["where"])
        assert "hidden_at IS NULL" in predicate


def test_deletion_marker_metadata_is_body_free_and_owner_idempotent() -> None:
    columns = set(OwnerDataDeletionRecord.__table__.columns.keys())
    assert {"marker_id", "owner_id", "scope", "affected_counts", "safe_reason"} <= columns
    assert not {"content", "payload", "puuid", "prompt"} & columns
    constraints = {
        value.name for value in OwnerDataDeletionRecord.__table__.constraints
    }
    assert "uq_owner_data_deletions_owner_idempotency" in constraints
