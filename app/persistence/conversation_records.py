from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class ConversationRecord(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    schema_version: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        server_default=sa.text("'1.0'"),
    )
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    player_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    relationship_role: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
    )
    request_fingerprint: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        server_default=sa.text("'active'"),
    )
    next_message_sequence: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
    )
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
    last_message_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    hidden_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )

    __table_args__ = (
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
        sa.CheckConstraint(
            "schema_version = '1.0'",
            name="schema_version_allowed",
        ),
        sa.CheckConstraint(
            "char_length(btrim(owner_id)) BETWEEN 1 AND 128",
            name="owner_id_bounded",
        ),
        sa.CheckConstraint(
            "char_length(btrim(idempotency_key)) BETWEEN 1 AND 128",
            name="idempotency_key_bounded",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="request_fingerprint_format",
        ),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'hidden')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "next_message_sequence >= 1",
            name="next_message_sequence_positive",
        ),
        sa.CheckConstraint(
            "((status IN ('active', 'archived') AND hidden_at IS NULL) OR "
            "(status = 'hidden' AND hidden_at IS NOT NULL))",
            name="hidden_status_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(last_message_at IS NULL OR "
            "(last_message_at >= created_at AND updated_at >= last_message_at)) AND "
            "(hidden_at IS NULL OR "
            "(hidden_at >= created_at AND updated_at >= hidden_at))",
            name="timestamp_order",
        ),
        sa.Index("ix_conversations_relationship_id", "relationship_id"),
        sa.Index("ix_conversations_player_subject_id", "player_subject_id"),
        sa.Index(
            "ix_conversations_owner_history",
            "owner_id",
            updated_at.desc(),
        ),
    )


class ConversationMessageRecord(Base):
    __tablename__ = "conversation_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    player_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    relationship_role: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_run_id: Mapped[str | None] = mapped_column(sa.String(128))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    hidden_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_conversation_messages_conversation_sequence",
        ),
        sa.UniqueConstraint(
            "message_id",
            "conversation_id",
            "owner_id",
            name="uq_conversation_messages_source_identity",
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
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "sequence_no >= 1",
            name="sequence_no_positive",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="role_allowed",
        ),
        sa.CheckConstraint(
            "char_length(content) BETWEEN 1 AND 16384 AND "
            "content ~ '[^[:space:]]'",
            name="content_bounded",
        ),
        sa.CheckConstraint(
            "content !~ U&'[\\0001-\\0008\\000B\\000C"
            "\\000E-\\001F\\007F-\\009F]'",
            name="content_control_characters_allowed",
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="content_sha256_format",
        ),
        sa.CheckConstraint(
            "role <> 'user' OR "
            "(source_task_id IS NULL AND source_run_id IS NULL)",
            name="user_source_empty",
        ),
        sa.CheckConstraint(
            "source_run_id IS NULL OR ("
            "char_length(source_run_id) BETWEEN 1 AND 128 AND "
            "source_run_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'"
            ")",
            name="source_run_id_bounded",
        ),
        sa.CheckConstraint(
            "role <> 'assistant' OR source_run_id IS NOT NULL",
            name="assistant_source_required",
        ),
        sa.CheckConstraint(
            "hidden_at IS NULL OR hidden_at >= created_at",
            name="timestamp_order",
        ),
        sa.Index(
            "ix_conversation_messages_relationship_id",
            "relationship_id",
        ),
        sa.Index(
            "ix_conversation_messages_player_subject_id",
            "player_subject_id",
        ),
        sa.Index(
            "ix_conversation_messages_source_task_id",
            "source_task_id",
        ),
        sa.Index(
            "ix_conversation_messages_source_run_id",
            "source_run_id",
        ),
        sa.Index(
            "uq_conversation_messages_assistant_source_run",
            "conversation_id",
            "source_run_id",
            unique=True,
            postgresql_where=sa.text("role = 'assistant'"),
        ),
    )


__all__ = ["ConversationMessageRecord", "ConversationRecord"]
