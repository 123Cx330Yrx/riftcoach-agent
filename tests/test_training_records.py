from app.persistence.training_records import TrainingPlanRecord, TrainingProgressRecord


def _names(items) -> set[str]:
    return {item.name for item in items if item.name is not None}


def test_training_tables_expose_identity_provenance_and_event_columns():
    assert {
        "plan_id",
        "source_candidate_id",
        "status_candidate_id",
        "owner_id",
        "source_conversation_id",
        "relationship_id",
        "player_subject_id",
        "relationship_role",
        "version",
        "status",
        "payload",
        "payload_sha256",
        "supersedes_plan_id",
        "created_at",
        "updated_at",
    } <= set(TrainingPlanRecord.__table__.columns.keys())
    assert {
        "progress_id",
        "plan_id",
        "source_candidate_id",
        "owner_id",
        "source_conversation_id",
        "relationship_id",
        "player_subject_id",
        "relationship_role",
        "metric_key",
        "metric_value",
        "observed_at",
        "source_task_id",
        "source_run_id",
        "source_artifact_sha256",
        "status",
        "supersedes_progress_id",
    } <= set(TrainingProgressRecord.__table__.columns.keys())


def test_training_plan_has_self_candidate_relationship_and_active_constraints():
    table = TrainingPlanRecord.__table__
    names = _names(table.constraints) | _names(table.indexes)
    assert {
        "fk_training_plans_candidate_identity",
        "fk_training_plans_status_candidate",
        "fk_training_plans_relationship_identity",
        "fk_training_plans_supersedes",
        "uq_training_plans_source_candidate",
        "uq_training_plans_status_candidate",
        "uq_training_plans_active_relationship",
        "ck_training_plans_self_only",
        "ck_training_plans_status_allowed",
    } <= names


def test_training_progress_has_plan_task_candidate_and_correction_constraints():
    table = TrainingProgressRecord.__table__
    names = _names(table.constraints) | _names(table.indexes)
    assert {
        "fk_training_progress_candidate_identity",
        "fk_training_progress_relationship_identity",
        "fk_training_progress_plan_identity",
        "fk_training_progress_task_identity",
        "fk_training_progress_supersedes",
        "uq_training_progress_source_candidate",
        "ck_training_progress_events_self_only",
        "ck_training_progress_events_status_allowed",
        "ck_training_progress_events_artifact_digest_format",
    } <= names
