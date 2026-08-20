from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class TrainingPlanRecord(Base):
    __tablename__ = "training_plans"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status_candidate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    source_conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    supersedes_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    hidden_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.UniqueConstraint(
            "source_candidate_id",
            name="uq_training_plans_source_candidate",
        ),
        sa.UniqueConstraint(
            "status_candidate_id",
            name="uq_training_plans_status_candidate",
        ),
        sa.UniqueConstraint(
            "plan_id",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            name="uq_training_plans_progress_identity",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "relationship_id",
            "version",
            name="uq_training_plans_relationship_version",
        ),
        sa.ForeignKeyConstraint(
            [
                "source_candidate_id",
                "owner_id",
                "source_conversation_id",
                "relationship_id",
                "player_subject_id",
                "relationship_role",
            ],
            [
                "memory_candidates.candidate_id",
                "memory_candidates.owner_id",
                "memory_candidates.conversation_id",
                "memory_candidates.relationship_id",
                "memory_candidates.player_subject_id",
                "memory_candidates.relationship_role",
            ],
            name="fk_training_plans_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["status_candidate_id"],
            ["memory_candidates.candidate_id"],
            name="fk_training_plans_status_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            [
                "owner_player_relationships.owner_id",
                "owner_player_relationships.relationship_id",
                "owner_player_relationships.player_subject_id",
                "owner_player_relationships.relationship_role",
            ],
            name="fk_training_plans_relationship_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_plan_id"],
            ["training_plans.plan_id"],
            name="fk_training_plans_supersedes",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name="schema_version_allowed"),
        sa.CheckConstraint("relationship_role = 'self'", name="self_only"),
        sa.CheckConstraint(
            "version >= 1 AND version <= 2147483647",
            name="version_range",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'abandoned', 'superseded')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "payload_sha256 ~ '^[0-9a-f]{64}$'",
            name="payload_digest_format",
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 12288",
            name="payload_storage_bound",
        ),
        sa.CheckConstraint(
            "version >= 1 AND (supersedes_plan_id IS NULL OR version > 1)",
            name="supersedes_shape",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND status_candidate_id IS NULL) OR "
            "(status <> 'active' AND status_candidate_id IS NOT NULL)",
            name="status_candidate_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(hidden_at IS NULL OR hidden_at >= created_at)",
            name="timestamp_order",
        ),
        sa.Index(
            "ix_training_plans_owner_history",
            "owner_id",
            "relationship_id",
            version.desc(),
        ),
        sa.Index(
            "uq_training_plans_active_relationship",
            "owner_id",
            "relationship_id",
            unique=True,
            postgresql_where=sa.text("status = 'active' AND hidden_at IS NULL"),
        ),
    )


class TrainingProgressRecord(Base):
    __tablename__ = "training_progress_events"

    progress_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    source_conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    metric_key: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    metric_value: Mapped[float] = mapped_column(sa.Float, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    source_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_run_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    source_artifact_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    supersedes_progress_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    hidden_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.UniqueConstraint(
            "source_candidate_id",
            name="uq_training_progress_source_candidate",
        ),
        sa.ForeignKeyConstraint(
            [
                "source_candidate_id",
                "owner_id",
                "source_conversation_id",
                "relationship_id",
                "player_subject_id",
                "relationship_role",
            ],
            [
                "memory_candidates.candidate_id",
                "memory_candidates.owner_id",
                "memory_candidates.conversation_id",
                "memory_candidates.relationship_id",
                "memory_candidates.player_subject_id",
                "memory_candidates.relationship_role",
            ],
            name="fk_training_progress_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            [
                "owner_player_relationships.owner_id",
                "owner_player_relationships.relationship_id",
                "owner_player_relationships.player_subject_id",
                "owner_player_relationships.relationship_role",
            ],
            name="fk_training_progress_relationship_identity",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            [
                "training_plans.plan_id",
                "training_plans.owner_id",
                "training_plans.relationship_id",
                "training_plans.player_subject_id",
                "training_plans.relationship_role",
            ],
            name="fk_training_progress_plan_identity",
        ),
        sa.ForeignKeyConstraint(
            [
                "source_task_id",
                "source_run_id",
                "source_conversation_id",
                "owner_id",
                "relationship_id",
                "player_subject_id",
                "relationship_role",
            ],
            [
                "review_tasks.task_id",
                "review_tasks.run_id",
                "review_tasks.conversation_id",
                "review_tasks.owner_id",
                "review_tasks.relationship_id",
                "review_tasks.player_subject_id",
                "review_tasks.relationship_role",
            ],
            name="fk_training_progress_task_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_progress_id"],
            ["training_progress_events.progress_id"],
            name="fk_training_progress_supersedes",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name="schema_version_allowed"),
        sa.CheckConstraint("relationship_role = 'self'", name="self_only"),
        sa.CheckConstraint(
            "status IN ('active', 'superseded')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "metric_key ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$'",
            name="metric_key_format",
        ),
        sa.CheckConstraint(
            "source_artifact_sha256 ~ '^[0-9a-f]{64}$'",
            name="artifact_digest_format",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(hidden_at IS NULL OR hidden_at >= created_at)",
            name="timestamp_order",
        ),
        sa.Index(
            "ix_training_progress_metric_history",
            "owner_id",
            "plan_id",
            "metric_key",
            observed_at.desc(),
            created_at.desc(),
        ),
        sa.Index("ix_training_progress_source_task", "source_task_id", "source_run_id"),
    )


__all__ = ["TrainingPlanRecord", "TrainingProgressRecord"]
