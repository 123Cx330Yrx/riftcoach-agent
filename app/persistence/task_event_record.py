from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class ReviewTaskEventRecord(Base):
    """Append-only, body-free lifecycle event for the SQL task control plane."""

    __tablename__ = "review_task_events"

    event_cursor: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.Identity(),
        primary_key=True,
    )
    event_identity: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        unique=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    task_sequence: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    event_kind: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    status_after: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    lease_generation: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(sa.String(128))
    operation_identity: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.String(64))
    checkpoint_reference: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True)
    )
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "task_id",
            "task_sequence",
            name="uq_review_task_events_task_sequence",
        ),
        sa.UniqueConstraint(
            "task_id",
            "operation_identity",
            name="uq_review_task_events_task_operation",
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "run_id", "owner_id"],
            [
                "review_tasks.task_id",
                "review_tasks.run_id",
                "review_tasks.owner_id",
            ],
            name="fk_review_task_events_task_identity",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "event_identity ~ '^[0-9a-f]{64}$'",
            name="event_identity_format",
        ),
        sa.CheckConstraint(
            "task_sequence >= 1 AND lease_generation >= 0",
            name="sequence_generation_non_negative",
        ),
        sa.CheckConstraint(
            "event_kind IN ('snapshot_imported', 'created', 'claimed', "
            "'heartbeat', 'checkpointed', 'execution_started', "
            "'cancel_requested', 'recovery_requeued', 'recovery_required', "
            "'succeeded', 'failed', 'cancelled', 'reconciled')",
            name="event_kind_allowed",
        ),
        sa.CheckConstraint(
            "status_after IN ('queued', 'running', 'recovery_required', "
            "'succeeded', 'failed', 'cancelled')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "operation_identity ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'",
            name="operation_identity_format",
        ),
        sa.CheckConstraint(
            "reason IS NULL OR "
            "reason ~ '^[a-z0-9]+([._-][a-z0-9]+)*$'",
            name="reason_format",
        ),
        sa.CheckConstraint(
            "checkpoint_reference IS NULL OR "
            "octet_length(checkpoint_reference::text) <= 2048",
            name="checkpoint_bound",
        ),
        sa.Index(
            "ix_review_task_events_owner_cursor",
            "owner_id",
            "event_cursor",
        ),
        sa.Index(
            "ix_review_task_events_task_cursor",
            "task_id",
            "event_cursor",
        ),
    )


__all__ = ["ReviewTaskEventRecord"]
