from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class ReviewTaskRecord(Base):
    """SQLAlchemy control-plane row; lifecycle behavior stays in the repository."""

    __tablename__ = "review_tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    run_id: Mapped[str] = mapped_column(sa.String(128), nullable=False, unique=True)
    task_kind: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)

    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    player_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    relationship_role: Mapped[str | None] = mapped_column(sa.String(16))

    status: Mapped[str] = mapped_column(
        sa.String(24),
        nullable=False,
        server_default=sa.text("'queued'"),
    )
    worker_id: Mapped[str | None] = mapped_column(sa.String(128))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    claimed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    lease_generation: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        server_default=sa.text("0"),
    )
    lease_token: Mapped[str | None] = mapped_column(sa.String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    cancel_request_id: Mapped[str | None] = mapped_column(sa.String(128))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    cancel_reason: Mapped[str | None] = mapped_column(sa.String(64))
    checkpoint_sequence: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        server_default=sa.text("0"),
    )
    checkpoint_reference: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True)
    )
    recovery_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    recovery_required_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    recovery_reason: Mapped[str | None] = mapped_column(sa.String(64))

    terminal_reason: Mapped[str | None] = mapped_column(sa.String(64))
    publication_status: Mapped[str | None] = mapped_column(sa.String(16))
    report_available: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.false(),
    )

    trace_reference: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    receipt_reference: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    artifact_reference: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_review_tasks_owner_id_idempotency_key",
        ),
        sa.UniqueConstraint(
            "task_id",
            "run_id",
            "owner_id",
            name="uq_review_tasks_event_identity",
        ),
        sa.UniqueConstraint(
            "task_id",
            "run_id",
            "conversation_id",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            name="uq_review_tasks_memory_source_identity",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'recovery_required', "
            "'succeeded', 'failed', 'cancelled')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "publication_status IS NULL OR "
            "publication_status IN ('published', 'degraded', 'rejected')",
            name="publication_status_allowed",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="request_fingerprint_format",
        ),
        sa.CheckConstraint(
            "schema_version IN ('1.0', '2.0')",
            name="schema_version_allowed",
        ),
        sa.CheckConstraint(
            "((schema_version = '1.0' AND conversation_id IS NULL "
            "AND relationship_id IS NULL AND player_subject_id IS NULL "
            "AND relationship_role IS NULL) OR "
            "(schema_version = '2.0' AND conversation_id IS NOT NULL "
            "AND relationship_id IS NOT NULL AND player_subject_id IS NOT NULL "
            "AND relationship_role IS NOT NULL))",
            name="schema_identity_shape",
        ),
        sa.CheckConstraint(
            "relationship_role IS NULL OR relationship_role IN ('self', 'observed')",
            name="conversation_role_allowed",
        ),
        sa.ForeignKeyConstraint(
            [
                "conversation_id",
                "owner_id",
                "relationship_id",
                "player_subject_id",
                "relationship_role",
            ],
            [
                "conversations.conversation_id",
                "conversations.owner_id",
                "conversations.relationship_id",
                "conversations.player_subject_id",
                "conversations.relationship_role",
            ],
            name="fk_review_tasks_conversation_identity",
        ),
        sa.CheckConstraint(
            "lease_generation >= 0 AND checkpoint_sequence >= 0 "
            "AND recovery_count >= 0",
            name="reliable_counters_non_negative",
        ),
        sa.CheckConstraint(
            "lease_token IS NULL OR lease_token ~ '^[0-9a-f]{64}$'",
            name="lease_token_format",
        ),
        sa.CheckConstraint(
            "(cancel_request_id IS NULL AND cancel_requested_at IS NULL "
            "AND cancel_reason IS NULL) OR "
            "(cancel_request_id IS NOT NULL AND cancel_requested_at IS NOT NULL "
            "AND cancel_reason IS NOT NULL)",
            name="cancel_request_shape",
        ),
        sa.CheckConstraint(
            "checkpoint_reference IS NULL OR "
            "(checkpoint_sequence >= 1 AND "
            "octet_length(checkpoint_reference::text) <= 2048)",
            name="checkpoint_shape",
        ),
        sa.CheckConstraint(
            "(status = 'queued' AND worker_id IS NULL AND claimed_at IS NULL "
            "AND finished_at IS NULL AND terminal_reason IS NULL "
            "AND lease_token IS NULL AND lease_expires_at IS NULL "
            "AND heartbeat_at IS NULL AND recovery_required_at IS NULL "
            "AND recovery_reason IS NULL AND cancel_request_id IS NULL) OR "
            "(status = 'running' AND worker_id IS NOT NULL "
            "AND claimed_at IS NOT NULL AND finished_at IS NULL "
            "AND terminal_reason IS NULL AND lease_generation >= 1 "
            "AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL "
            "AND heartbeat_at IS NOT NULL AND recovery_required_at IS NULL "
            "AND recovery_reason IS NULL) OR "
            "(status = 'recovery_required' AND worker_id IS NOT NULL "
            "AND claimed_at IS NOT NULL AND finished_at IS NULL "
            "AND terminal_reason IS NULL AND lease_generation >= 1 "
            "AND lease_token IS NULL AND lease_expires_at IS NULL "
            "AND heartbeat_at IS NOT NULL AND recovery_required_at IS NOT NULL "
            "AND recovery_reason IS NOT NULL AND cancel_request_id IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND worker_id IS NOT NULL "
            "AND claimed_at IS NOT NULL AND finished_at IS NOT NULL "
            "AND terminal_reason IS NOT NULL AND lease_generation >= 1 "
            "AND lease_token IS NULL AND lease_expires_at IS NULL "
            "AND heartbeat_at IS NOT NULL AND recovery_required_at IS NULL "
            "AND recovery_reason IS NULL AND cancel_request_id IS NULL) OR "
            "(status = 'cancelled' AND finished_at IS NOT NULL "
            "AND terminal_reason IS NOT NULL AND lease_token IS NULL "
            "AND lease_expires_at IS NULL AND recovery_required_at IS NULL "
            "AND recovery_reason IS NULL AND cancel_request_id IS NOT NULL AND "
            "((worker_id IS NULL AND claimed_at IS NULL "
            "AND heartbeat_at IS NULL AND lease_generation = 0) OR "
            "(worker_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND heartbeat_at IS NOT NULL AND lease_generation >= 1)))",
            name="reliable_lifecycle_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(claimed_at IS NULL OR claimed_at >= created_at) AND "
            "(heartbeat_at IS NULL OR "
            "(claimed_at IS NOT NULL AND heartbeat_at >= claimed_at)) AND "
            "(lease_expires_at IS NULL OR "
            "(heartbeat_at IS NOT NULL AND lease_expires_at > heartbeat_at)) AND "
            "(cancel_requested_at IS NULL OR "
            "cancel_requested_at >= created_at) AND "
            "(recovery_required_at IS NULL OR "
            "(claimed_at IS NOT NULL AND recovery_required_at >= claimed_at)) AND "
            "(finished_at IS NULL OR "
            "(finished_at >= created_at AND "
            "(claimed_at IS NULL OR finished_at >= claimed_at)))",
            name="timestamp_order",
        ),
        sa.Index("ix_review_tasks_claim", "status", "created_at", "task_id"),
        sa.Index(
            "ix_review_tasks_owner_history",
            "owner_id",
            created_at.desc(),
        ),
        sa.Index("ix_review_tasks_conversation_id", "conversation_id"),
        sa.Index("ix_review_tasks_relationship_id", "relationship_id"),
        sa.Index("ix_review_tasks_player_subject_id", "player_subject_id"),
        sa.Index(
            "ix_review_tasks_expired_lease",
            "status",
            "lease_expires_at",
            "task_id",
            postgresql_where=sa.text("status = 'running'"),
        ),
    )
