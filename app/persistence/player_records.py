from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


class PlayerSubjectRecord(Base):
    __tablename__ = "player_subjects"

    player_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    game: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    puuid: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    current_routing_region: Mapped[str] = mapped_column(sa.String(16), nullable=False)
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
    last_resolved_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "game",
            "puuid",
            name="uq_player_subjects_game_puuid",
        ),
        sa.CheckConstraint("game = 'lol'", name="game_allowed"),
        sa.CheckConstraint(
            "current_routing_region IN ('americas', 'asia', 'europe', 'sea')",
            name="current_routing_region_allowed",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND last_resolved_at >= created_at",
            name="timestamp_order",
        ),
    )


class PlayerAliasRecord(Base):
    __tablename__ = "player_aliases"

    player_alias_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    player_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey(
            "player_subjects.player_subject_id",
            name="fk_player_aliases_player_subject_id_player_subjects",
        ),
        nullable=False,
    )
    routing_region: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    game_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    tag_line: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    normalized_riot_id_hash: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "player_subject_id",
            "routing_region",
            "normalized_riot_id_hash",
            name="uq_player_aliases_subject_region_riot_id_hash",
        ),
        sa.CheckConstraint(
            "routing_region IN ('americas', 'asia', 'europe', 'sea')",
            name="routing_region_allowed",
        ),
        sa.CheckConstraint(
            "normalized_riot_id_hash ~ '^[0-9a-f]{64}$'",
            name="normalized_riot_id_hash_format",
        ),
        sa.CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="timestamp_order",
        ),
        sa.Index("ix_player_aliases_player_subject_id", "player_subject_id"),
    )


class OwnerPlayerRelationshipRecord(Base):
    __tablename__ = "owner_player_relationships"

    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    player_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey(
            "player_subjects.player_subject_id",
            name="fk_owner_player_relationships_player_subject_id_player_subjects",
        ),
        nullable=False,
    )
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    verification_status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        server_default=sa.text("'active'"),
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
    hidden_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    __table_args__ = (
        sa.UniqueConstraint(
            "owner_id",
            "player_subject_id",
            name="uq_owner_player_relationships_owner_id_player_subject_id",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            name="uq_owner_player_relationships_identity",
        ),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "verification_status IN ("
            "'unverified_claim', 'not_applicable', 'rso_verified'"
            ")",
            name="verification_status_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'hidden')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "("
            "(relationship_role = 'self' AND verification_status IN ("
            "'unverified_claim', 'rso_verified'"
            ")) OR "
            "(relationship_role = 'observed' AND verification_status = 'not_applicable')"
            ")",
            name="role_verification_allowed",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND hidden_at IS NULL) OR "
            "(status = 'hidden' AND hidden_at IS NOT NULL)",
            name="hidden_status_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(hidden_at IS NULL OR hidden_at >= created_at)",
            name="timestamp_order",
        ),
        sa.Index(
            "ix_owner_player_relationships_player_subject_id",
            "player_subject_id",
        ),
    )


class PlayerLinkTaskRecord(Base):
    __tablename__ = "player_link_tasks"

    link_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    task_kind: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        server_default=sa.text("'player_link'"),
    )
    schema_version: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        server_default=sa.text("'1.0'"),
    )
    owner_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    worker_id: Mapped[str | None] = mapped_column(sa.String(128))
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    game_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    tag_line: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    routing_region: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    relationship_role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    alias_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        server_default=sa.text("'queued'"),
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
    claimed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    terminal_reason: Mapped[str | None] = mapped_column(sa.String(64))
    confirmed_game_name: Mapped[str | None] = mapped_column(sa.String(64))
    confirmed_tag_line: Mapped[str | None] = mapped_column(sa.String(32))
    player_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey(
            "player_subjects.player_subject_id",
            name="fk_player_link_tasks_player_subject_id_player_subjects",
        ),
    )
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    __table_args__ = (
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_player_link_tasks_owner_id_idempotency_key",
        ),
        sa.CheckConstraint(
            "task_kind = 'player_link'",
            name="task_kind_allowed",
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'",
            name="schema_version_allowed",
        ),
        sa.CheckConstraint(
            "routing_region IN ('americas', 'asia', 'europe', 'sea')",
            name="routing_region_allowed",
        ),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="request_fingerprint_format",
        ),
        sa.CheckConstraint(
            "alias_hash ~ '^[0-9a-f]{64}$'",
            name="alias_hash_format",
        ),
        sa.CheckConstraint(
            "terminal_reason IS NULL OR "
            "terminal_reason ~ '^[a-z0-9]+(?:[._-][a-z0-9]+)*$'",
            name="terminal_reason_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(game_name)) BETWEEN 1 AND 64 AND "
            "char_length(btrim(tag_line)) BETWEEN 1 AND 32",
            name="riot_id_components_bounded",
        ),
        sa.CheckConstraint(
            "("
            "status = 'queued' AND worker_id IS NULL AND claimed_at IS NULL "
            "AND finished_at IS NULL AND terminal_reason IS NULL "
            "AND confirmed_game_name IS NULL AND confirmed_tag_line IS NULL "
            "AND player_subject_id IS NULL AND relationship_id IS NULL"
            ") OR ("
            "status = 'running' AND worker_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND finished_at IS NULL AND terminal_reason IS NULL "
            "AND confirmed_game_name IS NULL AND confirmed_tag_line IS NULL "
            "AND player_subject_id IS NULL AND relationship_id IS NULL"
            ") OR ("
            "status = 'succeeded' AND worker_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND terminal_reason IS NULL "
            "AND confirmed_game_name IS NOT NULL AND confirmed_tag_line IS NOT NULL "
            "AND player_subject_id IS NOT NULL AND relationship_id IS NOT NULL"
            ") OR ("
            "status = 'failed' AND worker_id IS NOT NULL AND claimed_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND terminal_reason IS NOT NULL "
            "AND confirmed_game_name IS NULL AND confirmed_tag_line IS NULL "
            "AND player_subject_id IS NULL AND relationship_id IS NULL"
            ")",
            name="lifecycle_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(claimed_at IS NULL OR claimed_at >= created_at) AND "
            "(finished_at IS NULL OR "
            "(claimed_at IS NOT NULL AND finished_at >= claimed_at))",
            name="timestamp_order",
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
            name="fk_player_link_tasks_relationship_identity",
        ),
        sa.Index(
            "ix_player_link_tasks_claim",
            "status",
            "created_at",
            "link_task_id",
        ),
        sa.Index(
            "ix_player_link_tasks_owner_history",
            "owner_id",
            created_at.desc(),
        ),
        sa.Index(
            "ix_player_link_tasks_player_subject_id",
            "player_subject_id",
        ),
        sa.Index(
            "ix_player_link_tasks_relationship_id",
            "relationship_id",
        ),
    )


__all__ = [
    "OwnerPlayerRelationshipRecord",
    "PlayerAliasRecord",
    "PlayerLinkTaskRecord",
    "PlayerSubjectRecord",
]
