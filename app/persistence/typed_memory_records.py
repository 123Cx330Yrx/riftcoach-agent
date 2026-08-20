from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


def _common_constraints() -> tuple[sa.CheckConstraint, ...]:
    return (
        sa.CheckConstraint("schema_version = '1.0'", name="schema_version_allowed"),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "version >= 1 AND version <= 2147483647",
            name="version_range",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'retired')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "payload_sha256 ~ '^[0-9a-f]{64}$'",
            name="payload_digest_format",
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 6144",
            name="payload_storage_bound",
        ),
        sa.CheckConstraint(
            "(version = 1 AND supersedes_record_id IS NULL) OR "
            "(version > 1 AND supersedes_record_id IS NOT NULL)",
            name="supersedes_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="timestamp_order",
        ),
    )


class MemoryPreferenceRecord(Base):
    __tablename__ = "memory_preferences"

    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    source_conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    memory_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supersedes_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("source_candidate_id", name="uq_memory_preferences_source_candidate"),
        sa.UniqueConstraint("owner_id", "memory_key", "version", name="uq_memory_preferences_version"),
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
            name="fk_memory_preferences_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_record_id"],
            ["memory_preferences.record_id"],
            name="fk_memory_preferences_supersedes",
        ),
        *_common_constraints(),
        sa.CheckConstraint("relationship_role = 'self'", name="self_only"),
        sa.CheckConstraint("memory_key = 'report_language'", name="memory_key_allowed"),
        sa.Index("ix_memory_preferences_owner_history", "owner_id", "memory_key", version.desc()),
        sa.Index(
            "uq_memory_preferences_active",
            "owner_id",
            "memory_key",
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        ),
    )


class PlayerProfileRecord(Base):
    __tablename__ = "player_profiles"

    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    source_conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    memory_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supersedes_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("source_candidate_id", name="uq_player_profiles_source_candidate"),
        sa.UniqueConstraint(
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "memory_key",
            "version",
            name="uq_player_profiles_version",
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
            name="fk_player_profiles_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            [
                "owner_player_relationships.owner_id",
                "owner_player_relationships.relationship_id",
                "owner_player_relationships.player_subject_id",
                "owner_player_relationships.relationship_role",
            ],
            name="fk_player_profiles_relationship_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_record_id"],
            ["player_profiles.record_id"],
            name="fk_player_profiles_supersedes",
        ),
        *_common_constraints(),
        sa.CheckConstraint("relationship_role = 'self'", name="self_only"),
        sa.CheckConstraint(
            "memory_key IN ('main_role', 'champion_pool')",
            name="memory_key_allowed",
        ),
        sa.Index(
            "ix_player_profiles_owner_history",
            "owner_id",
            "relationship_id",
            "memory_key",
            version.desc(),
        ),
        sa.Index(
            "uq_player_profiles_active",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "memory_key",
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        ),
    )


class ReviewMemoryRecord(Base):
    __tablename__ = "review_memories"

    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    source_conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    memory_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    source_candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supersedes_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("source_candidate_id", name="uq_review_memories_source_candidate"),
        sa.UniqueConstraint(
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            "memory_key",
            "version",
            name="uq_review_memories_version",
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
            name="fk_review_memories_candidate_identity",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
            [
                "owner_player_relationships.owner_id",
                "owner_player_relationships.relationship_id",
                "owner_player_relationships.player_subject_id",
                "owner_player_relationships.relationship_role",
            ],
            name="fk_review_memories_relationship_identity",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_record_id"],
            ["review_memories.record_id"],
            name="fk_review_memories_supersedes",
        ),
        *_common_constraints(),
        sa.CheckConstraint(
            "memory_key IN ('review_summary', 'observation_note', 'public_trend')",
            name="memory_key_allowed",
        ),
        sa.CheckConstraint(
            "relationship_role <> 'observed' OR "
            "memory_key IN ('observation_note', 'public_trend')",
            name="observed_key_allowed",
        ),
        sa.Index(
            "ix_review_memories_owner_history",
            "owner_id",
            "relationship_id",
            "relationship_role",
            "memory_key",
            version.desc(),
        ),
        sa.Index(
            "uq_review_memories_active",
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            "memory_key",
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        ),
    )


__all__ = ["MemoryPreferenceRecord", "PlayerProfileRecord", "ReviewMemoryRecord"]
