from __future__ import annotations

import sqlalchemy as sa

from tests.memory_candidate_postgres_support import migrated_memory_repository


def _names(items) -> set[str]:
    return {item["name"] for item in items if item.get("name")}


def test_training_migration_exposes_tables_indexes_and_foreign_keys():
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        assert {"training_plans", "training_progress_events"} <= set(inspector.get_table_names())
        assert "uq_training_plans_active_relationship" in _names(inspector.get_indexes("training_plans"))
        assert {
            "fk_training_plans_candidate_identity",
            "fk_training_plans_relationship_identity",
            "fk_training_plans_supersedes",
        } <= _names(inspector.get_foreign_keys("training_plans"))
        assert {
            "fk_training_progress_candidate_identity",
            "fk_training_progress_plan_identity",
            "fk_training_progress_task_identity",
            "fk_training_progress_supersedes",
        } <= _names(inspector.get_foreign_keys("training_progress_events"))


def test_training_migration_exposes_self_status_and_artifact_checks():
    with migrated_memory_repository() as (_repository, _factory, engine):
        inspector = sa.inspect(engine)
        assert {
            "ck_training_plans_self_only",
            "ck_training_plans_status_allowed",
            "ck_training_plans_status_candidate_shape",
        } <= _names(inspector.get_check_constraints("training_plans"))
        assert {
            "ck_training_progress_events_self_only",
            "ck_training_progress_events_status_allowed",
            "ck_training_progress_events_artifact_digest_format",
        } <= _names(inspector.get_check_constraints("training_progress_events"))
