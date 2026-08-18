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

    status: Mapped[str] = mapped_column(
        sa.String(16),
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
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
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
            "(status = 'queued' AND worker_id IS NULL AND claimed_at IS NULL "
            "AND finished_at IS NULL AND terminal_reason IS NULL) OR "
            "(status = 'running' AND worker_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND finished_at IS NULL AND terminal_reason IS NULL) OR "
            "(status IN ('succeeded', 'failed') AND worker_id IS NOT NULL "
            "AND claimed_at IS NOT NULL AND finished_at IS NOT NULL "
            "AND terminal_reason IS NOT NULL)",
            name="lifecycle_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(claimed_at IS NULL OR claimed_at >= created_at) AND "
            "(finished_at IS NULL OR "
            "(claimed_at IS NOT NULL AND finished_at >= claimed_at))",
            name="timestamp_order",
        ),
        sa.Index("ix_review_tasks_claim", "status", "created_at", "task_id"),
        sa.Index(
            "ix_review_tasks_owner_history",
            "owner_id",
            created_at.desc(),
        ),
    )
