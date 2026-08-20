"""Create Training Plan and Progress event targets.

Revision ID: 0007_training_plan_progress
Revises: 0006_typed_memory_targets
Create Date: 2026-08-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0007_training_plan_progress"
down_revision: str | None = "0006_typed_memory_targets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_plans",
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("source_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status_candidate_id", postgresql.UUID(as_uuid=True)),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("source_conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_role", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("supersedes_plan_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("plan_id", name="pk_training_plans"),
        sa.UniqueConstraint("source_candidate_id", name="uq_training_plans_source_candidate"),
        sa.UniqueConstraint("status_candidate_id", name="uq_training_plans_status_candidate"),
        sa.UniqueConstraint(
            "plan_id", "owner_id", "relationship_id", "player_subject_id", "relationship_role",
            name="uq_training_plans_progress_identity",
        ),
        sa.UniqueConstraint(
            "owner_id", "relationship_id", "version",
            name="uq_training_plans_relationship_version",
        ),
        sa.ForeignKeyConstraint(
            ["source_candidate_id", "owner_id", "source_conversation_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["memory_candidates.candidate_id", "memory_candidates.owner_id", "memory_candidates.conversation_id", "memory_candidates.relationship_id", "memory_candidates.player_subject_id", "memory_candidates.relationship_role"],
            name="fk_training_plans_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["status_candidate_id"], ["memory_candidates.candidate_id"],
            name="fk_training_plans_status_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["owner_player_relationships.owner_id", "owner_player_relationships.relationship_id", "owner_player_relationships.player_subject_id", "owner_player_relationships.relationship_role"],
            name="fk_training_plans_relationship_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_plan_id"], ["training_plans.plan_id"],
            name="fk_training_plans_supersedes",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_training_plans_schema_version_allowed")),
        sa.CheckConstraint("relationship_role = 'self'", name=op.f("ck_training_plans_self_only")),
        sa.CheckConstraint("version >= 1 AND version <= 2147483647", name=op.f("ck_training_plans_version_range")),
        sa.CheckConstraint("status IN ('active', 'completed', 'abandoned', 'superseded')", name=op.f("ck_training_plans_status_allowed")),
        sa.CheckConstraint("payload_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_training_plans_payload_digest_format")),
        sa.CheckConstraint("octet_length(payload::text) <= 12288", name=op.f("ck_training_plans_payload_storage_bound")),
        sa.CheckConstraint("(version = 1 AND supersedes_plan_id IS NULL) OR (version > 1 AND supersedes_plan_id IS NOT NULL)", name=op.f("ck_training_plans_supersedes_shape")),
        sa.CheckConstraint("(status = 'active' AND status_candidate_id IS NULL) OR (status <> 'active' AND status_candidate_id IS NOT NULL)", name=op.f("ck_training_plans_status_candidate_shape")),
        sa.CheckConstraint("updated_at >= created_at", name=op.f("ck_training_plans_timestamp_order")),
    )
    op.create_index(
        "ix_training_plans_owner_history",
        "training_plans",
        ["owner_id", "relationship_id", sa.text("version DESC")],
    )
    op.create_index(
        "uq_training_plans_active_relationship",
        "training_plans",
        ["owner_id", "relationship_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "training_progress_events",
        sa.Column("progress_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("source_conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_role", sa.String(16), nullable=False),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_run_id", sa.String(128), nullable=False),
        sa.Column("source_artifact_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("supersedes_progress_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("progress_id", name="pk_training_progress_events"),
        sa.UniqueConstraint("source_candidate_id", name="uq_training_progress_source_candidate"),
        sa.ForeignKeyConstraint(
            ["source_candidate_id", "owner_id", "source_conversation_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["memory_candidates.candidate_id", "memory_candidates.owner_id", "memory_candidates.conversation_id", "memory_candidates.relationship_id", "memory_candidates.player_subject_id", "memory_candidates.relationship_role"],
            name="fk_training_progress_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["owner_player_relationships.owner_id", "owner_player_relationships.relationship_id", "owner_player_relationships.player_subject_id", "owner_player_relationships.relationship_role"],
            name="fk_training_progress_relationship_identity",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["training_plans.plan_id", "training_plans.owner_id", "training_plans.relationship_id", "training_plans.player_subject_id", "training_plans.relationship_role"],
            name="fk_training_progress_plan_identity",
        ),
        sa.ForeignKeyConstraint(
            ["source_task_id", "source_run_id", "source_conversation_id", "owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["review_tasks.task_id", "review_tasks.run_id", "review_tasks.conversation_id", "review_tasks.owner_id", "review_tasks.relationship_id", "review_tasks.player_subject_id", "review_tasks.relationship_role"],
            name="fk_training_progress_task_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_progress_id"], ["training_progress_events.progress_id"],
            name="fk_training_progress_supersedes",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_training_progress_events_schema_version_allowed")),
        sa.CheckConstraint("relationship_role = 'self'", name=op.f("ck_training_progress_events_self_only")),
        sa.CheckConstraint("status IN ('active', 'superseded')", name=op.f("ck_training_progress_events_status_allowed")),
        sa.CheckConstraint("metric_key ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$'", name=op.f("ck_training_progress_events_metric_key_format")),
        sa.CheckConstraint("source_artifact_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_training_progress_events_artifact_digest_format")),
        sa.CheckConstraint("updated_at >= created_at", name=op.f("ck_training_progress_events_timestamp_order")),
    )
    op.create_index(
        "ix_training_progress_metric_history",
        "training_progress_events",
        ["owner_id", "plan_id", "metric_key", sa.text("observed_at DESC"), sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_training_progress_source_task",
        "training_progress_events",
        ["source_task_id", "source_run_id"],
    )

    _create_validation_functions()
    op.execute("CREATE TRIGGER trg_training_plans_validate BEFORE INSERT OR UPDATE ON training_plans FOR EACH ROW EXECUTE FUNCTION riftcoach_validate_training_plan()")
    op.execute("CREATE TRIGGER trg_training_progress_validate BEFORE INSERT OR UPDATE ON training_progress_events FOR EACH ROW EXECUTE FUNCTION riftcoach_validate_training_progress()")


def _create_validation_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION riftcoach_validate_training_plan()
        RETURNS trigger AS $$
        DECLARE source_row memory_candidates%ROWTYPE;
        DECLARE previous_row training_plans%ROWTYPE;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                SELECT * INTO source_row FROM memory_candidates WHERE candidate_id = NEW.source_candidate_id;
                IF NOT FOUND OR source_row.status <> 'pending' OR source_row.candidate_kind <> 'training_plan'
                   OR source_row.target_scope <> 'owner_player' OR source_row.operation <> 'set'
                   OR source_row.relationship_role <> 'self' OR source_row.requires_confirmation IS NOT TRUE THEN
                    RAISE EXCEPTION 'training_plan_source_invalid' USING ERRCODE = '23514';
                END IF;
                IF NEW.version > 1 THEN
                    SELECT * INTO previous_row FROM training_plans WHERE plan_id = NEW.supersedes_plan_id;
                    IF NOT FOUND OR previous_row.owner_id <> NEW.owner_id
                       OR previous_row.relationship_id <> NEW.relationship_id
                       OR previous_row.version + 1 <> NEW.version THEN
                        RAISE EXCEPTION 'training_plan_supersedes_invalid' USING ERRCODE = '23514';
                    END IF;
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.status <> 'active' OR NEW.status NOT IN ('completed', 'abandoned', 'superseded')
               OR NEW.status_candidate_id IS NULL
               OR (OLD.plan_id, OLD.source_candidate_id, OLD.owner_id, OLD.source_conversation_id,
                   OLD.relationship_id, OLD.player_subject_id, OLD.relationship_role, OLD.version,
                   OLD.payload, OLD.payload_sha256, OLD.supersedes_plan_id, OLD.created_at)
                  IS DISTINCT FROM
                  (NEW.plan_id, NEW.source_candidate_id, NEW.owner_id, NEW.source_conversation_id,
                   NEW.relationship_id, NEW.player_subject_id, NEW.relationship_role, NEW.version,
                   NEW.payload, NEW.payload_sha256, NEW.supersedes_plan_id, NEW.created_at)
               OR NEW.updated_at < OLD.updated_at THEN
                RAISE EXCEPTION 'training_plan_update_forbidden' USING ERRCODE = '23514';
            END IF;
            SELECT * INTO source_row FROM memory_candidates WHERE candidate_id = NEW.status_candidate_id;
            IF NOT FOUND OR source_row.status <> 'pending' OR source_row.candidate_kind <> 'training_plan'
               OR source_row.owner_id <> NEW.owner_id OR source_row.relationship_id <> NEW.relationship_id
               OR source_row.relationship_role <> 'self' THEN
                RAISE EXCEPTION 'training_plan_status_source_invalid' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE FUNCTION riftcoach_validate_training_progress()
        RETURNS trigger AS $$
        DECLARE source_row memory_candidates%ROWTYPE;
        DECLARE task_row review_tasks%ROWTYPE;
        DECLARE plan_row training_plans%ROWTYPE;
        DECLARE old_event training_progress_events%ROWTYPE;
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                IF OLD.status <> 'active' OR NEW.status <> 'superseded'
                   OR (OLD.progress_id, OLD.plan_id, OLD.source_candidate_id, OLD.owner_id,
                       OLD.source_conversation_id, OLD.relationship_id, OLD.player_subject_id,
                       OLD.relationship_role, OLD.metric_key, OLD.metric_value, OLD.observed_at,
                       OLD.source_task_id, OLD.source_run_id, OLD.source_artifact_sha256,
                       OLD.supersedes_progress_id, OLD.created_at)
                      IS DISTINCT FROM
                      (NEW.progress_id, NEW.plan_id, NEW.source_candidate_id, NEW.owner_id,
                       NEW.source_conversation_id, NEW.relationship_id, NEW.player_subject_id,
                       NEW.relationship_role, NEW.metric_key, NEW.metric_value, NEW.observed_at,
                       NEW.source_task_id, NEW.source_run_id, NEW.source_artifact_sha256,
                       NEW.supersedes_progress_id, NEW.created_at)
                   OR NEW.updated_at < OLD.updated_at THEN
                    RAISE EXCEPTION 'training_progress_update_forbidden' USING ERRCODE = '23514';
                END IF;
                RETURN NEW;
            END IF;
            SELECT * INTO source_row FROM memory_candidates WHERE candidate_id = NEW.source_candidate_id;
            IF NOT FOUND OR source_row.status <> 'pending' OR source_row.candidate_kind <> 'training_progress'
               OR source_row.target_scope <> 'owner_player' OR source_row.operation <> 'append'
               OR source_row.provenance_kind <> 'deterministic_run_fact' OR source_row.relationship_role <> 'self'
               OR source_row.source_task_id <> NEW.source_task_id OR source_row.source_run_id <> NEW.source_run_id
               OR source_row.source_artifact_sha256 <> NEW.source_artifact_sha256 THEN
                RAISE EXCEPTION 'training_progress_source_invalid' USING ERRCODE = '23514';
            END IF;
            SELECT * INTO plan_row FROM training_plans WHERE plan_id = NEW.plan_id AND status = 'active';
            IF NOT FOUND OR plan_row.owner_id <> NEW.owner_id OR plan_row.relationship_id <> NEW.relationship_id
               OR NOT (plan_row.payload->'metrics' @> jsonb_build_array(jsonb_build_object('metric_key', NEW.metric_key))) THEN
                RAISE EXCEPTION 'training_progress_plan_metric_invalid' USING ERRCODE = '23514';
            END IF;
            SELECT * INTO task_row FROM review_tasks WHERE task_id = NEW.source_task_id AND run_id = NEW.source_run_id;
            IF NOT FOUND OR task_row.status <> 'succeeded' OR task_row.publication_status NOT IN ('published', 'degraded')
               OR task_row.report_available IS NOT TRUE OR task_row.artifact_reference IS NULL
               OR task_row.artifact_reference->>'kind' <> 'final_report'
               OR task_row.artifact_reference->>'sha256' <> NEW.source_artifact_sha256 THEN
                RAISE EXCEPTION 'training_progress_artifact_invalid' USING ERRCODE = '23514';
            END IF;
            IF NEW.supersedes_progress_id IS NOT NULL THEN
                SELECT * INTO old_event FROM training_progress_events WHERE progress_id = NEW.supersedes_progress_id;
                IF NOT FOUND OR old_event.status <> 'active' OR old_event.plan_id <> NEW.plan_id
                   OR old_event.metric_key <> NEW.metric_key OR old_event.owner_id <> NEW.owner_id THEN
                    RAISE EXCEPTION 'training_progress_correction_invalid' USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_training_progress_validate ON training_progress_events")
    op.execute("DROP TRIGGER IF EXISTS trg_training_plans_validate ON training_plans")
    op.execute("DROP FUNCTION IF EXISTS riftcoach_validate_training_progress()")
    op.execute("DROP FUNCTION IF EXISTS riftcoach_validate_training_plan()")
    op.drop_table("training_progress_events")
    op.drop_table("training_plans")
