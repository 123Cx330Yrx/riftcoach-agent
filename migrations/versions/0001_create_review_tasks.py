"""Create the durable review task control table.

Revision ID: 0001_review_tasks
Revises: None
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_review_tasks"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_tasks",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("task_kind", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_reason", sa.String(length=64), nullable=True),
        sa.Column("publication_status", sa.String(length=16), nullable=True),
        sa.Column(
            "report_available",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("trace_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("receipt_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("artifact_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("task_id", name="pk_review_tasks"),
        sa.UniqueConstraint("run_id", name="uq_review_tasks_run_id"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_review_tasks_owner_id_idempotency_key",
        ),
    )
    op.create_index(
        "ix_review_tasks_claim",
        "review_tasks",
        ["status", "created_at", "task_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_tasks_owner_history",
        "review_tasks",
        ["owner_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_review_tasks_owner_history", table_name="review_tasks")
    op.drop_index("ix_review_tasks_claim", table_name="review_tasks")
    op.drop_table("review_tasks")
