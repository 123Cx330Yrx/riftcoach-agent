from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class MemoryCandidateRecord(Base):
    __tablename__ = "memory_candidates"

    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    source_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_run_id: Mapped[str | None] = mapped_column(sa.String(128))
    source_artifact_sha256: Mapped[str | None] = mapped_column(sa.String(64))

    target_scope: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    candidate_kind: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    memory_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    operation: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    proposal_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    proposal_payload_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    provenance_kind: Mapped[str] = mapped_column(sa.String(48), nullable=False)
    producer_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    producer_version: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    proposal_confidence: Mapped[float | None] = mapped_column(sa.Numeric(4, 3))
    gate_policy_version: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    requires_confirmation: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    decision_actor_kind: Mapped[str | None] = mapped_column(sa.String(16))
    decision_actor_id: Mapped[str | None] = mapped_column(sa.String(128))
    decision_reason_code: Mapped[str | None] = mapped_column(sa.String(64))
    decided_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    materialized_target_kind: Mapped[str | None] = mapped_column(sa.String(128))
    materialized_target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    materializer_version: Mapped[str | None] = mapped_column(sa.String(64))

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_memory_candidates_owner_id_idempotency_key",
        ),
        sa.UniqueConstraint(
            "candidate_id",
            "owner_id",
            "conversation_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            name="uq_memory_candidates_identity",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name="schema_version_allowed"),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "target_scope IN ('owner_global', 'owner_player')",
            name="target_scope_allowed",
        ),
        sa.CheckConstraint(
            "candidate_kind IN ('owner_preference', 'player_profile', 'review_memory', 'training_plan', 'training_progress')",
            name="candidate_kind_allowed",
        ),
        sa.CheckConstraint("operation IN ('set', 'append')", name="operation_allowed"),
        sa.CheckConstraint(
            "provenance_kind IN ('user_structured_input', 'user_message_extraction', 'model_inference', 'deterministic_run_fact', 'published_review_observation')",
            name="provenance_kind_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "decision_actor_kind IS NULL OR decision_actor_kind IN ('user', 'system')",
            name="decision_actor_kind_allowed",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$' AND proposal_payload_sha256 ~ '^[0-9a-f]{64}$'",
            name="digest_format",
        ),
        sa.CheckConstraint(
            "proposal_confidence IS NULL OR (proposal_confidence >= 0 AND proposal_confidence <= 1)",
            name="confidence_range",
        ),
        sa.CheckConstraint(
            "(target_scope = 'owner_global' AND candidate_kind = 'owner_preference') OR "
            "(target_scope = 'owner_player' AND candidate_kind <> 'owner_preference')",
            name="scope_kind_shape",
        ),
        sa.CheckConstraint(
            "(source_task_id IS NULL AND source_run_id IS NULL) OR "
            "(source_task_id IS NOT NULL AND source_run_id IS NOT NULL)",
            name="source_run_requires_task",
        ),
        sa.CheckConstraint(
            "source_artifact_sha256 IS NULL OR "
            "(source_task_id IS NOT NULL AND source_artifact_sha256 ~ '^[0-9a-f]{64}$')",
            name="source_artifact_shape",
        ),
        sa.CheckConstraint(
            "relationship_role <> 'observed' OR "
            "(candidate_kind = 'review_memory' AND operation = 'append' "
            "AND memory_key IN ('observation_note', 'public_trend'))",
            name="observed_candidate_shape",
        ),
        sa.CheckConstraint(
            "provenance_kind NOT IN ('model_inference', 'user_message_extraction') "
            "OR requires_confirmation",
            name="inference_requires_confirmation",
        ),
        sa.CheckConstraint(
            "candidate_kind <> 'training_plan' OR requires_confirmation",
            name="training_plan_requires_confirmation",
        ),
        sa.CheckConstraint(
            "octet_length(proposal_payload::text) <= 12288",
            name="payload_storage_bound",
        ),
        sa.CheckConstraint(
            "((status = 'pending' AND decision_actor_kind IS NULL AND decision_actor_id IS NULL AND decision_reason_code IS NULL AND decided_at IS NULL AND materialized_target_kind IS NULL AND materialized_target_id IS NULL AND materializer_version IS NULL) OR "
            "(status = 'accepted' AND decision_actor_kind IS NOT NULL AND decision_actor_id IS NOT NULL AND decision_reason_code IS NOT NULL AND decided_at IS NOT NULL AND materialized_target_kind IS NOT NULL AND materialized_target_id IS NOT NULL AND materializer_version IS NOT NULL) OR "
            "(status IN ('rejected', 'expired') AND decision_actor_kind IS NOT NULL AND decision_actor_id IS NOT NULL AND decision_reason_code IS NOT NULL AND decided_at IS NOT NULL AND materialized_target_kind IS NULL AND materialized_target_id IS NULL AND materializer_version IS NULL))",
            name="status_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND expires_at > created_at AND (decided_at IS NULL OR decided_at >= created_at)",
            name="timestamp_order",
        ),
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
        sa.Index("ix_memory_candidates_owner_pending", "owner_id", "status", "created_at"),
        sa.Index("ix_memory_candidates_conversation_history", "owner_id", "conversation_id", "created_at"),
        sa.Index("ix_memory_candidates_expiry", "status", "expires_at"),
    )


__all__ = ["MemoryCandidateRecord"]
