"""Add owner data lifecycle visibility and deletion markers.

Revision ID: 0009_owner_data_lifecycle
Revises: 0008_terminal_assistant
Create Date: 2026-08-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0009_owner_data_lifecycle"
down_revision: str | None = "0008_terminal_assistant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRIVATE_TABLES = (
    "memory_candidates",
    "memory_preferences",
    "player_profiles",
    "review_memories",
    "training_plans",
    "training_progress_events",
)


def upgrade() -> None:
    for table_name in _PRIVATE_TABLES:
        op.add_column(
            table_name,
            sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        )

    for table_name in _PRIVATE_TABLES:
        op.drop_constraint(
            op.f(f"ck_{table_name}_timestamp_order"), table_name, type_="check"
        )
    op.create_check_constraint(
        op.f("ck_memory_candidates_timestamp_order"),
        "memory_candidates",
        "updated_at >= created_at AND expires_at > created_at AND "
        "(decided_at IS NULL OR decided_at >= created_at) AND "
        "(hidden_at IS NULL OR hidden_at >= created_at)",
    )
    for table_name in _PRIVATE_TABLES[1:]:
        op.create_check_constraint(
            op.f(f"ck_{table_name}_timestamp_order"),
            table_name,
            "updated_at >= created_at AND "
            "(hidden_at IS NULL OR hidden_at >= created_at)",
        )

    _replace_supersedes_constraints(lifecycle_reset=True)

    _replace_active_indexes(hidden=True)

    op.create_table(
        "owner_data_deletions",
        sa.Column("marker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("affected_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safe_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("marker_id", name="pk_owner_data_deletions"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_owner_data_deletions_owner_idempotency",
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_owner_data_deletions_schema_version_allowed")),
        sa.CheckConstraint(
            "scope IN ('conversation_only', 'conversation_and_derived_memory', 'relationship_private_data')",
            name=op.f("ck_owner_data_deletions_scope_allowed"),
        ),
        sa.CheckConstraint(
            "((scope IN ('conversation_only', 'conversation_and_derived_memory') AND "
            "conversation_id IS NOT NULL AND relationship_id IS NULL) OR "
            "(scope = 'relationship_private_data' AND conversation_id IS NULL AND relationship_id IS NOT NULL))",
            name=op.f("ck_owner_data_deletions_target_shape"),
        ),
        sa.CheckConstraint(
            "status IN ('cleanup_pending', 'complete')",
            name=op.f("ck_owner_data_deletions_status_allowed"),
        ),
        sa.CheckConstraint(
            "octet_length(affected_counts::text) <= 2048",
            name=op.f("ck_owner_data_deletions_affected_counts_bound"),
        ),
        sa.CheckConstraint(
            "((status = 'cleanup_pending' AND completed_at IS NULL) OR "
            "(status = 'complete' AND safe_reason IS NULL AND completed_at IS NOT NULL))",
            name=op.f("ck_owner_data_deletions_status_shape"),
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND (completed_at IS NULL OR completed_at >= created_at)",
            name=op.f("ck_owner_data_deletions_timestamp_order"),
        ),
    )
    op.create_index(
        "ix_owner_data_deletions_pending",
        "owner_data_deletions",
        ["owner_id", "status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_owner_data_deletions_pending", table_name="owner_data_deletions")
    op.drop_table("owner_data_deletions")
    _replace_active_indexes(hidden=False)
    _replace_supersedes_constraints(lifecycle_reset=False)
    for table_name in _PRIVATE_TABLES:
        op.drop_constraint(
            op.f(f"ck_{table_name}_timestamp_order"), table_name, type_="check"
        )
    op.create_check_constraint(
        op.f("ck_memory_candidates_timestamp_order"),
        "memory_candidates",
        "updated_at >= created_at AND expires_at > created_at AND "
        "(decided_at IS NULL OR decided_at >= created_at)",
    )
    for table_name in _PRIVATE_TABLES[1:]:
        op.create_check_constraint(
            op.f(f"ck_{table_name}_timestamp_order"),
            table_name,
            "updated_at >= created_at",
        )
    for table_name in reversed(_PRIVATE_TABLES):
        op.drop_column(table_name, "hidden_at")


def _replace_active_indexes(*, hidden: bool) -> None:
    definitions = (
        ("uq_memory_preferences_active", "memory_preferences", ["owner_id", "memory_key"]),
        (
            "uq_player_profiles_active",
            "player_profiles",
            ["owner_id", "relationship_id", "player_subject_id", "memory_key"],
        ),
        (
            "uq_review_memories_active",
            "review_memories",
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role", "memory_key"],
        ),
        (
            "uq_training_plans_active_relationship",
            "training_plans",
            ["owner_id", "relationship_id"],
        ),
    )
    predicate = "status = 'active' AND hidden_at IS NULL" if hidden else "status = 'active'"
    for name, table_name, columns in definitions:
        op.drop_index(name, table_name=table_name)
        op.create_index(
            name,
            table_name,
            columns,
            unique=True,
            postgresql_where=sa.text(predicate),
        )


def _replace_supersedes_constraints(*, lifecycle_reset: bool) -> None:
    definitions = (
        ("memory_preferences", "supersedes_record_id"),
        ("player_profiles", "supersedes_record_id"),
        ("review_memories", "supersedes_record_id"),
        ("training_plans", "supersedes_plan_id"),
    )
    for table_name, column_name in definitions:
        op.drop_constraint(
            op.f(f"ck_{table_name}_supersedes_shape"),
            table_name,
            type_="check",
        )
        if lifecycle_reset:
            expression = (
                f"version >= 1 AND ({column_name} IS NULL OR version > 1)"
            )
        else:
            expression = (
                f"(version = 1 AND {column_name} IS NULL) OR "
                f"(version > 1 AND {column_name} IS NOT NULL)"
            )
        op.create_check_constraint(
            op.f(f"ck_{table_name}_supersedes_shape"),
            table_name,
            expression,
        )
