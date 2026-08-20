import sqlalchemy as sa

from tests.memory_candidate_postgres_support import migrated_memory_repository


def test_0009_adds_hidden_columns_marker_and_partial_unique_predicates() -> None:
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        for table in (
            "memory_candidates",
            "memory_preferences",
            "player_profiles",
            "review_memories",
            "training_plans",
            "training_progress_events",
        ):
            assert "hidden_at" in {row["name"] for row in inspector.get_columns(table)}

        assert "owner_data_deletions" in inspector.get_table_names()
        indexes = {
            row["name"]: row for row in inspector.get_indexes("training_plans")
        }
        predicate = str(
            indexes["uq_training_plans_active_relationship"]
            .get("dialect_options", {})
            .get("postgresql_where", "")
        )
        assert "hidden_at" in predicate
