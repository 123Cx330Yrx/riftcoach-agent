"""Bind schema 2.0 review tasks to immutable Conversation identity.

Revision ID: 0004_review_task_identity
Revises: 0003_conversation_messages
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004_review_task_identity"
down_revision: str | None = "0003_conversation_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_tasks",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "relationship_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "player_subject_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column("relationship_role", sa.String(length=16), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_schema_version_allowed"),
        "review_tasks",
        "schema_version IN ('1.0', '2.0')",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_schema_identity_shape"),
        "review_tasks",
        "((schema_version = '1.0' AND conversation_id IS NULL "
        "AND relationship_id IS NULL AND player_subject_id IS NULL "
        "AND relationship_role IS NULL) OR "
        "(schema_version = '2.0' AND conversation_id IS NOT NULL "
        "AND relationship_id IS NOT NULL AND player_subject_id IS NOT NULL "
        "AND relationship_role IS NOT NULL))",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_conversation_role_allowed"),
        "review_tasks",
        "relationship_role IS NULL OR "
        "relationship_role IN ('self', 'observed')",
    )
    op.create_foreign_key(
        "fk_review_tasks_conversation_identity",
        "review_tasks",
        "conversations",
        [
            "conversation_id",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
        ],
        [
            "conversation_id",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
        ],
    )
    op.create_index(
        "ix_review_tasks_conversation_id",
        "review_tasks",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_tasks_relationship_id",
        "review_tasks",
        ["relationship_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_tasks_player_subject_id",
        "review_tasks",
        ["player_subject_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION riftcoach_guard_review_task_identity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF ROW(
                NEW.task_id,
                NEW.run_id,
                NEW.task_kind,
                NEW.schema_version,
                NEW.owner_id,
                NEW.idempotency_key,
                NEW.request_fingerprint,
                NEW.request_payload,
                NEW.conversation_id,
                NEW.relationship_id,
                NEW.player_subject_id,
                NEW.relationship_role,
                NEW.created_at
            ) IS DISTINCT FROM ROW(
                OLD.task_id,
                OLD.run_id,
                OLD.task_kind,
                OLD.schema_version,
                OLD.owner_id,
                OLD.idempotency_key,
                OLD.request_fingerprint,
                OLD.request_payload,
                OLD.conversation_id,
                OLD.relationship_id,
                OLD.player_subject_id,
                OLD.relationship_role,
                OLD.created_at
            ) THEN
                RAISE EXCEPTION 'review_task_identity_immutable'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_review_tasks_guard_identity
        BEFORE UPDATE ON review_tasks
        FOR EACH ROW
        EXECUTE FUNCTION riftcoach_guard_review_task_identity()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_review_tasks_guard_identity "
        "ON review_tasks"
    )
    op.execute("DROP FUNCTION IF EXISTS riftcoach_guard_review_task_identity()")
    op.drop_index("ix_review_tasks_player_subject_id", table_name="review_tasks")
    op.drop_index("ix_review_tasks_relationship_id", table_name="review_tasks")
    op.drop_index("ix_review_tasks_conversation_id", table_name="review_tasks")
    op.drop_constraint(
        "fk_review_tasks_conversation_identity",
        "review_tasks",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_conversation_role_allowed"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_schema_identity_shape"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_schema_version_allowed"),
        "review_tasks",
        type_="check",
    )
    op.drop_column("review_tasks", "relationship_role")
    op.drop_column("review_tasks", "player_subject_id")
    op.drop_column("review_tasks", "relationship_id")
    op.drop_column("review_tasks", "conversation_id")
