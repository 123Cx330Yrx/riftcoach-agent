"""Create server-derived Memory Candidate write-gate control plane.

Revision ID: 0005_memory_candidates
Revises: 0004_review_task_identity
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0005_memory_candidates"
down_revision: str | None = "0004_review_task_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # These stable source identities let a Candidate prove that an optional
    # message/task/run belongs to the same Conversation identity.
    op.create_unique_constraint(
        "uq_conversation_messages_source_identity",
        "conversation_messages",
        ["message_id", "conversation_id", "owner_id"],
    )
    op.create_unique_constraint(
        "uq_review_tasks_memory_source_identity",
        "review_tasks",
        [
            "task_id",
            "run_id",
            "conversation_id",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
        ],
    )

    op.create_table(
        "memory_candidates",
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_role", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_run_id", sa.String(length=128), nullable=True),
        sa.Column("source_artifact_sha256", sa.String(length=64), nullable=True),
        sa.Column("target_scope", sa.String(length=32), nullable=False),
        sa.Column("candidate_kind", sa.String(length=32), nullable=False),
        sa.Column("memory_key", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("proposal_payload", postgresql.JSONB, nullable=False),
        sa.Column("proposal_payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("provenance_kind", sa.String(length=48), nullable=False),
        sa.Column("producer_id", sa.String(length=128), nullable=False),
        sa.Column("producer_version", sa.String(length=64), nullable=False),
        sa.Column("proposal_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("gate_policy_version", sa.String(length=64), nullable=False),
        sa.Column("requires_confirmation", sa.Boolean, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("decision_actor_kind", sa.String(length=16), nullable=True),
        sa.Column("decision_actor_id", sa.String(length=128), nullable=True),
        sa.Column("decision_reason_code", sa.String(length=64), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("materialized_target_kind", sa.String(length=128), nullable=True),
        sa.Column("materialized_target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("materializer_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("candidate_id", name="pk_memory_candidates"),
        sa.UniqueConstraint("owner_id", "idempotency_key", name="uq_memory_candidates_owner_id_idempotency_key"),
        sa.UniqueConstraint(
            "candidate_id",
            "owner_id",
            "conversation_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            name="uq_memory_candidates_identity",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_memory_candidates_schema_version_allowed")),
        sa.CheckConstraint("relationship_role IN ('self', 'observed')", name=op.f("ck_memory_candidates_relationship_role_allowed")),
        sa.CheckConstraint("target_scope IN ('owner_global', 'owner_player')", name=op.f("ck_memory_candidates_target_scope_allowed")),
        sa.CheckConstraint("candidate_kind IN ('owner_preference', 'player_profile', 'review_memory', 'training_plan', 'training_progress')", name=op.f("ck_memory_candidates_candidate_kind_allowed")),
        sa.CheckConstraint("operation IN ('set', 'append')", name=op.f("ck_memory_candidates_operation_allowed")),
        sa.CheckConstraint("provenance_kind IN ('user_structured_input', 'user_message_extraction', 'model_inference', 'deterministic_run_fact', 'published_review_observation')", name=op.f("ck_memory_candidates_provenance_kind_allowed")),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'expired')", name=op.f("ck_memory_candidates_status_allowed")),
        sa.CheckConstraint("decision_actor_kind IS NULL OR decision_actor_kind IN ('user', 'system')", name=op.f("ck_memory_candidates_decision_actor_kind_allowed")),
        sa.CheckConstraint("request_fingerprint ~ '^[0-9a-f]{64}$' AND proposal_payload_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_memory_candidates_digest_format")),
        sa.CheckConstraint("proposal_confidence IS NULL OR (proposal_confidence >= 0 AND proposal_confidence <= 1)", name=op.f("ck_memory_candidates_confidence_range")),
        sa.CheckConstraint("(target_scope = 'owner_global' AND candidate_kind = 'owner_preference') OR (target_scope = 'owner_player' AND candidate_kind <> 'owner_preference')", name=op.f("ck_memory_candidates_scope_kind_shape")),
        sa.CheckConstraint("(source_task_id IS NULL AND source_run_id IS NULL) OR (source_task_id IS NOT NULL AND source_run_id IS NOT NULL)", name=op.f("ck_memory_candidates_source_run_requires_task")),
        sa.CheckConstraint("source_artifact_sha256 IS NULL OR (source_task_id IS NOT NULL AND source_artifact_sha256 ~ '^[0-9a-f]{64}$')", name=op.f("ck_memory_candidates_source_artifact_shape")),
        sa.CheckConstraint("relationship_role <> 'observed' OR (candidate_kind = 'review_memory' AND operation = 'append' AND memory_key IN ('observation_note', 'public_trend'))", name=op.f("ck_memory_candidates_observed_candidate_shape")),
        sa.CheckConstraint("provenance_kind NOT IN ('model_inference', 'user_message_extraction') OR requires_confirmation", name=op.f("ck_memory_candidates_inference_requires_confirmation")),
        sa.CheckConstraint("candidate_kind <> 'training_plan' OR requires_confirmation", name=op.f("ck_memory_candidates_training_plan_requires_confirmation")),
        sa.CheckConstraint("octet_length(proposal_payload::text) <= 12288", name=op.f("ck_memory_candidates_payload_storage_bound")),
        sa.CheckConstraint(
            "((status = 'pending' AND decision_actor_kind IS NULL AND decision_actor_id IS NULL AND decision_reason_code IS NULL AND decided_at IS NULL AND materialized_target_kind IS NULL AND materialized_target_id IS NULL AND materializer_version IS NULL) OR "
            "(status = 'accepted' AND decision_actor_kind IS NOT NULL AND decision_actor_id IS NOT NULL AND decision_reason_code IS NOT NULL AND decided_at IS NOT NULL AND materialized_target_kind IS NOT NULL AND materialized_target_id IS NOT NULL AND materializer_version IS NOT NULL) OR "
            "(status IN ('rejected', 'expired') AND decision_actor_kind IS NOT NULL AND decision_actor_id IS NOT NULL AND decision_reason_code IS NOT NULL AND decided_at IS NOT NULL AND materialized_target_kind IS NULL AND materialized_target_id IS NULL AND materializer_version IS NULL))",
            name=op.f("ck_memory_candidates_status_shape"),
        ),
        sa.CheckConstraint("updated_at >= created_at AND expires_at > created_at AND (decided_at IS NULL OR decided_at >= created_at)", name=op.f("ck_memory_candidates_timestamp_order")),
        sa.ForeignKeyConstraint(
            ["conversation_id", "owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["conversations.conversation_id", "conversations.owner_id", "conversations.relationship_id", "conversations.player_subject_id", "conversations.relationship_role"],
            name="fk_memory_candidates_conversation_identity",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "conversation_id", "owner_id"],
            ["conversation_messages.message_id", "conversation_messages.conversation_id", "conversation_messages.owner_id"],
            name="fk_memory_candidates_source_message",
        ),
        sa.ForeignKeyConstraint(
            ["source_task_id", "source_run_id", "conversation_id", "owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            ["review_tasks.task_id", "review_tasks.run_id", "review_tasks.conversation_id", "review_tasks.owner_id", "review_tasks.relationship_id", "review_tasks.player_subject_id", "review_tasks.relationship_role"],
            name="fk_memory_candidates_source_task",
        ),
    )
    op.create_index("ix_memory_candidates_owner_pending", "memory_candidates", ["owner_id", "status", "created_at"])
    op.create_index("ix_memory_candidates_conversation_history", "memory_candidates", ["owner_id", "conversation_id", "created_at"])
    op.create_index("ix_memory_candidates_expiry", "memory_candidates", ["status", "expires_at"])

    op.execute(
        """
        CREATE FUNCTION riftcoach_guard_memory_candidate_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF ROW(
                NEW.candidate_id, NEW.schema_version, NEW.owner_id, NEW.conversation_id,
                NEW.relationship_id, NEW.player_subject_id, NEW.relationship_role,
                NEW.idempotency_key, NEW.request_fingerprint, NEW.source_message_id,
                NEW.source_task_id, NEW.source_run_id, NEW.source_artifact_sha256,
                NEW.target_scope, NEW.candidate_kind, NEW.memory_key, NEW.operation,
                NEW.proposal_payload, NEW.proposal_payload_sha256, NEW.provenance_kind,
                NEW.producer_id, NEW.producer_version, NEW.proposal_confidence,
                NEW.gate_policy_version, NEW.requires_confirmation
            ) IS DISTINCT FROM ROW(
                OLD.candidate_id, OLD.schema_version, OLD.owner_id, OLD.conversation_id,
                OLD.relationship_id, OLD.player_subject_id, OLD.relationship_role,
                OLD.idempotency_key, OLD.request_fingerprint, OLD.source_message_id,
                OLD.source_task_id, OLD.source_run_id, OLD.source_artifact_sha256,
                OLD.target_scope, OLD.candidate_kind, OLD.memory_key, OLD.operation,
                OLD.proposal_payload, OLD.proposal_payload_sha256, OLD.provenance_kind,
                OLD.producer_id, OLD.producer_version, OLD.proposal_confidence,
                OLD.gate_policy_version, OLD.requires_confirmation
            ) THEN
                RAISE EXCEPTION 'memory_candidate_identity_or_proposal_immutable' USING ERRCODE = '23514';
            END IF;
            IF OLD.status <> 'pending' AND NEW IS DISTINCT FROM OLD THEN
                RAISE EXCEPTION 'memory_candidate_terminal_immutable' USING ERRCODE = '23514';
            END IF;
            IF OLD.status = 'pending' AND NEW.status NOT IN ('pending', 'accepted', 'rejected', 'expired') THEN
                RAISE EXCEPTION 'memory_candidate_invalid_transition' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_memory_candidates_guard_update
        BEFORE UPDATE ON memory_candidates
        FOR EACH ROW EXECUTE FUNCTION riftcoach_guard_memory_candidate_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_memory_candidates_guard_update ON memory_candidates")
    op.execute("DROP FUNCTION IF EXISTS riftcoach_guard_memory_candidate_update()")
    op.drop_index("ix_memory_candidates_expiry", table_name="memory_candidates")
    op.drop_index("ix_memory_candidates_conversation_history", table_name="memory_candidates")
    op.drop_index("ix_memory_candidates_owner_pending", table_name="memory_candidates")
    op.drop_table("memory_candidates")
    op.drop_constraint("uq_review_tasks_memory_source_identity", "review_tasks", type_="unique")
    op.drop_constraint("uq_conversation_messages_source_identity", "conversation_messages", type_="unique")
