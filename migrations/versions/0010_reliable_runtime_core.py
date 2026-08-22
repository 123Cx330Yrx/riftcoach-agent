"""Add leased, fenced and replayable task control-plane state.

Revision ID: 0010_reliable_runtime_core
Revises: 0009_owner_data_lifecycle
Create Date: 2026-08-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0010_reliable_runtime_core"
down_revision: str | None = "0009_owner_data_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_tasks",
        sa.Column(
            "lease_generation",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column("lease_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column("cancel_request_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column("cancel_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "checkpoint_sequence",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "checkpoint_reference",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "recovery_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "recovery_required_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column("recovery_reason", sa.String(length=64), nullable=True),
    )
    op.alter_column(
        "review_tasks",
        "status",
        existing_type=sa.String(length=16),
        type_=sa.String(length=24),
        existing_nullable=False,
    )

    op.drop_constraint(
        op.f("ck_review_tasks_status_allowed"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_lifecycle_shape"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_timestamp_order"),
        "review_tasks",
        type_="check",
    )

    op.execute(
        """
        UPDATE review_tasks
        SET lease_generation = CASE WHEN claimed_at IS NULL THEN 0 ELSE 1 END,
            heartbeat_at = claimed_at
        """
    )
    op.execute(
        """
        UPDATE review_tasks
        SET status = 'recovery_required',
            recovery_required_at = GREATEST(now(), updated_at, claimed_at),
            recovery_reason = 'migration_requires_recovery',
            updated_at = GREATEST(now(), updated_at, claimed_at)
        WHERE status = 'running'
        """
    )

    op.create_unique_constraint(
        "uq_review_tasks_event_identity",
        "review_tasks",
        ["task_id", "run_id", "owner_id"],
    )
    _create_reliable_task_constraints()
    op.create_index(
        "ix_review_tasks_expired_lease",
        "review_tasks",
        ["status", "lease_expires_at", "task_id"],
        unique=False,
        postgresql_where=sa.text("status = 'running'"),
    )

    op.create_table(
        "review_task_events",
        sa.Column(
            "event_cursor",
            sa.BigInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column("event_identity", sa.String(length=64), nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("task_sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_kind", sa.String(length=32), nullable=False),
        sa.Column("status_after", sa.String(length=24), nullable=False),
        sa.Column("lease_generation", sa.BigInteger(), nullable=False),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("operation_identity", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column(
            "checkpoint_reference",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_identity ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_review_task_events_event_identity_format"),
        ),
        sa.CheckConstraint(
            "task_sequence >= 1 AND lease_generation >= 0",
            name=op.f("ck_review_task_events_sequence_generation_non_negative"),
        ),
        sa.CheckConstraint(
            "event_kind IN ('snapshot_imported', 'created', 'claimed', "
            "'heartbeat', 'checkpointed', 'execution_started', "
            "'cancel_requested', 'recovery_requeued', 'recovery_required', "
            "'succeeded', 'failed', 'cancelled', 'reconciled')",
            name=op.f("ck_review_task_events_event_kind_allowed"),
        ),
        sa.CheckConstraint(
            "status_after IN ('queued', 'running', 'recovery_required', "
            "'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_review_task_events_status_allowed"),
        ),
        sa.CheckConstraint(
            "operation_identity ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'",
            name=op.f("ck_review_task_events_operation_identity_format"),
        ),
        sa.CheckConstraint(
            "reason IS NULL OR "
            "reason ~ '^[a-z0-9]+([._-][a-z0-9]+)*$'",
            name=op.f("ck_review_task_events_reason_format"),
        ),
        sa.CheckConstraint(
            "checkpoint_reference IS NULL OR "
            "octet_length(checkpoint_reference::text) <= 2048",
            name=op.f("ck_review_task_events_checkpoint_bound"),
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
        sa.PrimaryKeyConstraint(
            "event_cursor",
            name=op.f("pk_review_task_events"),
        ),
        sa.UniqueConstraint(
            "event_identity",
            name=op.f("uq_review_task_events_event_identity"),
        ),
        sa.UniqueConstraint(
            "task_id",
            "operation_identity",
            name="uq_review_task_events_task_operation",
        ),
        sa.UniqueConstraint(
            "task_id",
            "task_sequence",
            name="uq_review_task_events_task_sequence",
        ),
    )
    op.create_index(
        "ix_review_task_events_owner_cursor",
        "review_task_events",
        ["owner_id", "event_cursor"],
        unique=False,
    )
    op.create_index(
        "ix_review_task_events_task_cursor",
        "review_task_events",
        ["task_id", "event_cursor"],
        unique=False,
    )

    _bootstrap_snapshot_events()


def downgrade() -> None:
    op.drop_index(
        "ix_review_task_events_task_cursor",
        table_name="review_task_events",
    )
    op.drop_index(
        "ix_review_task_events_owner_cursor",
        table_name="review_task_events",
    )
    op.drop_table("review_task_events")
    op.drop_index("ix_review_tasks_expired_lease", table_name="review_tasks")

    _drop_reliable_task_constraints()
    op.drop_constraint(
        "uq_review_tasks_event_identity",
        "review_tasks",
        type_="unique",
    )

    op.execute(
        """
        UPDATE review_tasks
        SET status = 'failed',
            finished_at = GREATEST(now(), claimed_at, updated_at),
            terminal_reason = 'recovery_required_downgrade',
            publication_status = NULL,
            report_available = false,
            trace_reference = NULL,
            receipt_reference = NULL,
            artifact_reference = NULL
        WHERE status = 'recovery_required'
        """
    )
    op.execute(
        """
        UPDATE review_tasks
        SET status = 'failed',
            worker_id = COALESCE(worker_id, 'migration-0010-downgrade'),
            claimed_at = COALESCE(claimed_at, created_at),
            finished_at = GREATEST(
                now(), COALESCE(claimed_at, created_at), updated_at
            ),
            terminal_reason = 'cancelled_downgrade',
            publication_status = NULL,
            report_available = false,
            trace_reference = NULL,
            receipt_reference = NULL,
            artifact_reference = NULL
        WHERE status = 'cancelled'
        """
    )

    op.alter_column(
        "review_tasks",
        "status",
        existing_type=sa.String(length=24),
        type_=sa.String(length=16),
        existing_nullable=False,
    )

    op.create_check_constraint(
        op.f("ck_review_tasks_status_allowed"),
        "review_tasks",
        "status IN ('queued', 'running', 'succeeded', 'failed')",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_lifecycle_shape"),
        "review_tasks",
        "(status = 'queued' AND worker_id IS NULL AND claimed_at IS NULL "
        "AND finished_at IS NULL AND terminal_reason IS NULL) OR "
        "(status = 'running' AND worker_id IS NOT NULL AND claimed_at IS NOT NULL "
        "AND finished_at IS NULL AND terminal_reason IS NULL) OR "
        "(status IN ('succeeded', 'failed') AND worker_id IS NOT NULL "
        "AND claimed_at IS NOT NULL AND finished_at IS NOT NULL "
        "AND terminal_reason IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_timestamp_order"),
        "review_tasks",
        "updated_at >= created_at AND "
        "(claimed_at IS NULL OR claimed_at >= created_at) AND "
        "(finished_at IS NULL OR "
        "(claimed_at IS NOT NULL AND finished_at >= claimed_at))",
    )

    for column_name in (
        "recovery_reason",
        "recovery_required_at",
        "recovery_count",
        "checkpoint_reference",
        "checkpoint_sequence",
        "cancel_reason",
        "cancel_requested_at",
        "cancel_request_id",
        "heartbeat_at",
        "lease_expires_at",
        "lease_token",
        "lease_generation",
    ):
        op.drop_column("review_tasks", column_name)


def _create_reliable_task_constraints() -> None:
    op.create_check_constraint(
        op.f("ck_review_tasks_status_allowed"),
        "review_tasks",
        "status IN ('queued', 'running', 'recovery_required', "
        "'succeeded', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_reliable_counters_non_negative"),
        "review_tasks",
        "lease_generation >= 0 AND checkpoint_sequence >= 0 "
        "AND recovery_count >= 0",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_lease_token_format"),
        "review_tasks",
        "lease_token IS NULL OR lease_token ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_cancel_request_shape"),
        "review_tasks",
        "(cancel_request_id IS NULL AND cancel_requested_at IS NULL "
        "AND cancel_reason IS NULL) OR "
        "(cancel_request_id IS NOT NULL AND cancel_requested_at IS NOT NULL "
        "AND cancel_reason IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_checkpoint_shape"),
        "review_tasks",
        "checkpoint_reference IS NULL OR "
        "(checkpoint_sequence >= 1 AND "
        "octet_length(checkpoint_reference::text) <= 2048)",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_reliable_lifecycle_shape"),
        "review_tasks",
        _reliable_lifecycle_expression(),
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_timestamp_order"),
        "review_tasks",
        _reliable_timestamp_expression(),
    )


def _drop_reliable_task_constraints() -> None:
    for constraint_name in (
        "ck_review_tasks_timestamp_order",
        "ck_review_tasks_reliable_lifecycle_shape",
        "ck_review_tasks_checkpoint_shape",
        "ck_review_tasks_cancel_request_shape",
        "ck_review_tasks_lease_token_format",
        "ck_review_tasks_reliable_counters_non_negative",
        "ck_review_tasks_status_allowed",
    ):
        op.drop_constraint(
            op.f(constraint_name),
            "review_tasks",
            type_="check",
        )


def _reliable_lifecycle_expression() -> str:
    return (
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
        "AND heartbeat_at IS NOT NULL AND lease_generation >= 1)))"
    )


def _reliable_timestamp_expression() -> str:
    return (
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
        "(claimed_at IS NULL OR finished_at >= claimed_at)))"
    )


def _bootstrap_snapshot_events() -> None:
    separator = "chr(31)"
    identity_components = (
        "'1.0'",
        "task_id::text",
        "run_id",
        "owner_id",
        "'1'",
        "'snapshot_imported'",
        "status",
        "lease_generation::text",
        "COALESCE(worker_id, '')",
        "'snapshot-import-0010'",
        "COALESCE(recovery_reason, terminal_reason, '')",
        "''",
        "''",
        "''",
        "''",
        "''",
        "to_char(updated_at AT TIME ZONE 'UTC', "
        "'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')",
    )
    identity_sql = f" || {separator} || ".join(identity_components)
    op.execute(
        f"""
        INSERT INTO review_task_events (
            event_identity, task_id, run_id, owner_id, task_sequence,
            event_kind, status_after, lease_generation, worker_id,
            operation_identity, reason, checkpoint_reference, occurred_at
        )
        SELECT
            encode(sha256(convert_to({identity_sql}, 'UTF8')), 'hex'),
            task_id, run_id, owner_id, 1, 'snapshot_imported', status,
            lease_generation, worker_id, 'snapshot-import-0010',
            COALESCE(recovery_reason, terminal_reason), NULL, updated_at
        FROM review_tasks
        """
    )
