"""Create immutable-subject conversations and ordered messages.

Revision ID: 0003_conversation_messages
Revises: 0002_player_identity_link
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0003_conversation_messages"
down_revision: str | None = "0002_player_identity_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column(
            "relationship_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "player_subject_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "relationship_role",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "next_message_sequence",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
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
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "schema_version = '1.0'",
            name=op.f("ck_conversations_schema_version_allowed"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(owner_id)) BETWEEN 1 AND 128",
            name=op.f("ck_conversations_owner_id_bounded"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(idempotency_key)) BETWEEN 1 AND 128",
            name=op.f("ck_conversations_idempotency_key_bounded"),
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_conversations_request_fingerprint_format"),
        ),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name=op.f("ck_conversations_relationship_role_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'hidden')",
            name=op.f("ck_conversations_status_allowed"),
        ),
        sa.CheckConstraint(
            "next_message_sequence >= 1",
            name=op.f("ck_conversations_next_message_sequence_positive"),
        ),
        sa.CheckConstraint(
            "((status IN ('active', 'archived') AND hidden_at IS NULL) OR "
            "(status = 'hidden' AND hidden_at IS NOT NULL))",
            name=op.f("ck_conversations_hidden_status_shape"),
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(last_message_at IS NULL OR "
            "(last_message_at >= created_at AND updated_at >= last_message_at)) AND "
            "(hidden_at IS NULL OR "
            "(hidden_at >= created_at AND updated_at >= hidden_at))",
            name=op.f("ck_conversations_timestamp_order"),
        ),
        sa.ForeignKeyConstraint(
            [
                "owner_id",
                "relationship_id",
                "player_subject_id",
                "relationship_role",
            ],
            [
                "owner_player_relationships.owner_id",
                "owner_player_relationships.relationship_id",
                "owner_player_relationships.player_subject_id",
                "owner_player_relationships.relationship_role",
            ],
            name="fk_conversations_relationship_identity",
        ),
        sa.PrimaryKeyConstraint("conversation_id", name="pk_conversations"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_conversations_owner_id_idempotency_key",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            name="uq_conversations_identity",
        ),
    )
    op.create_index(
        "ix_conversations_relationship_id",
        "conversations",
        ["relationship_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_player_subject_id",
        "conversations",
        ["player_subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_owner_history",
        "conversations",
        ["owner_id", sa.text("updated_at DESC")],
        unique=False,
    )

    op.create_table(
        "conversation_messages",
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column(
            "relationship_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "player_subject_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "relationship_role",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "source_task_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("source_run_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name=op.f(
                "ck_conversation_messages_relationship_role_allowed"
            ),
        ),
        sa.CheckConstraint(
            "sequence_no >= 1",
            name=op.f("ck_conversation_messages_sequence_no_positive"),
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name=op.f("ck_conversation_messages_role_allowed"),
        ),
        sa.CheckConstraint(
            "char_length(content) BETWEEN 1 AND 16384 AND "
            "content ~ '[^[:space:]]'",
            name=op.f("ck_conversation_messages_content_bounded"),
        ),
        sa.CheckConstraint(
            "content !~ U&'[\\0001-\\0008\\000B\\000C"
            "\\000E-\\001F\\007F-\\009F]'",
            name=op.f(
                "ck_conversation_messages_content_control_characters_allowed"
            ),
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_conversation_messages_content_sha256_format"),
        ),
        sa.CheckConstraint(
            "role <> 'user' OR "
            "(source_task_id IS NULL AND source_run_id IS NULL)",
            name=op.f("ck_conversation_messages_user_source_empty"),
        ),
        sa.CheckConstraint(
            "source_run_id IS NULL OR ("
            "char_length(source_run_id) BETWEEN 1 AND 128 AND "
            "source_run_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'"
            ")",
            name=op.f("ck_conversation_messages_source_run_id_bounded"),
        ),
        sa.CheckConstraint(
            "role <> 'assistant' OR source_run_id IS NOT NULL",
            name=op.f("ck_conversation_messages_assistant_source_required"),
        ),
        sa.CheckConstraint(
            "hidden_at IS NULL OR hidden_at >= created_at",
            name=op.f("ck_conversation_messages_timestamp_order"),
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
            name="fk_conversation_messages_conversation_identity",
        ),
        sa.PrimaryKeyConstraint(
            "message_id",
            name="pk_conversation_messages",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_conversation_messages_conversation_sequence",
        ),
    )
    op.create_index(
        "ix_conversation_messages_relationship_id",
        "conversation_messages",
        ["relationship_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_messages_player_subject_id",
        "conversation_messages",
        ["player_subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_messages_source_task_id",
        "conversation_messages",
        ["source_task_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_messages_source_run_id",
        "conversation_messages",
        ["source_run_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION riftcoach_guard_conversation_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF ROW(
                NEW.conversation_id,
                NEW.schema_version,
                NEW.owner_id,
                NEW.relationship_id,
                NEW.player_subject_id,
                NEW.relationship_role,
                NEW.idempotency_key,
                NEW.request_fingerprint,
                NEW.created_at
            ) IS DISTINCT FROM ROW(
                OLD.conversation_id,
                OLD.schema_version,
                OLD.owner_id,
                OLD.relationship_id,
                OLD.player_subject_id,
                OLD.relationship_role,
                OLD.idempotency_key,
                OLD.request_fingerprint,
                OLD.created_at
            ) THEN
                RAISE EXCEPTION 'conversation_binding_immutable'
                    USING ERRCODE = '23514';
            END IF;

            IF NOT (
                NEW.status = OLD.status
                OR (OLD.status = 'active' AND NEW.status IN ('archived', 'hidden'))
                OR (OLD.status = 'archived' AND NEW.status = 'hidden')
            ) THEN
                RAISE EXCEPTION 'conversation_lifecycle_irreversible'
                    USING ERRCODE = '23514';
            END IF;

            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_conversations_guard_update
        BEFORE UPDATE ON conversations
        FOR EACH ROW
        EXECUTE FUNCTION riftcoach_guard_conversation_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION riftcoach_guard_conversation_message_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF ROW(
                NEW.message_id,
                NEW.conversation_id,
                NEW.owner_id,
                NEW.relationship_id,
                NEW.player_subject_id,
                NEW.relationship_role,
                NEW.sequence_no,
                NEW.role,
                NEW.content,
                NEW.content_sha256,
                NEW.source_task_id,
                NEW.source_run_id,
                NEW.created_at
            ) IS DISTINCT FROM ROW(
                OLD.message_id,
                OLD.conversation_id,
                OLD.owner_id,
                OLD.relationship_id,
                OLD.player_subject_id,
                OLD.relationship_role,
                OLD.sequence_no,
                OLD.role,
                OLD.content,
                OLD.content_sha256,
                OLD.source_task_id,
                OLD.source_run_id,
                OLD.created_at
            ) THEN
                RAISE EXCEPTION 'conversation_message_immutable'
                    USING ERRCODE = '23514';
            END IF;

            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_conversation_messages_guard_update
        BEFORE UPDATE ON conversation_messages
        FOR EACH ROW
        EXECUTE FUNCTION riftcoach_guard_conversation_message_update()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_conversation_messages_guard_update "
        "ON conversation_messages"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS riftcoach_guard_conversation_message_update()"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_conversations_guard_update ON conversations"
    )
    op.execute("DROP FUNCTION IF EXISTS riftcoach_guard_conversation_update()")

    op.drop_index(
        "ix_conversation_messages_source_run_id",
        table_name="conversation_messages",
    )
    op.drop_index(
        "ix_conversation_messages_source_task_id",
        table_name="conversation_messages",
    )
    op.drop_index(
        "ix_conversation_messages_player_subject_id",
        table_name="conversation_messages",
    )
    op.drop_index(
        "ix_conversation_messages_relationship_id",
        table_name="conversation_messages",
    )
    op.drop_table("conversation_messages")

    op.drop_index(
        "ix_conversations_owner_history",
        table_name="conversations",
    )
    op.drop_index(
        "ix_conversations_player_subject_id",
        table_name="conversations",
    )
    op.drop_index(
        "ix_conversations_relationship_id",
        table_name="conversations",
    )
    op.drop_table("conversations")
