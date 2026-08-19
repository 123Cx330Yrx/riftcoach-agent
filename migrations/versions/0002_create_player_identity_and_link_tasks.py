"""Create player identity and link task persistence tables.

Revision ID: 0002_player_identity_link
Revises: 0001_review_tasks
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0002_player_identity_link"
down_revision: str | None = "0001_review_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_subjects",
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game", sa.String(length=16), nullable=False),
        sa.Column("puuid", sa.String(length=128), nullable=False),
        sa.Column("current_routing_region", sa.String(length=16), nullable=False),
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
            "last_resolved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("game = 'lol'", name="ck_player_subjects_game_allowed"),
        sa.CheckConstraint(
            "current_routing_region IN ('americas', 'asia', 'europe', 'sea')",
            name="ck_player_subjects_current_routing_region_allowed",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND last_resolved_at >= created_at",
            name="ck_player_subjects_timestamp_order",
        ),
        sa.PrimaryKeyConstraint(
            "player_subject_id",
            name="pk_player_subjects",
        ),
        sa.UniqueConstraint("game", "puuid", name="uq_player_subjects_game_puuid"),
    )

    op.create_table(
        "player_aliases",
        sa.Column("player_alias_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routing_region", sa.String(length=16), nullable=False),
        sa.Column("game_name", sa.String(length=64), nullable=False),
        sa.Column("tag_line", sa.String(length=32), nullable=False),
        sa.Column("normalized_riot_id_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "routing_region IN ('americas', 'asia', 'europe', 'sea')",
            name="ck_player_aliases_routing_region_allowed",
        ),
        sa.CheckConstraint(
            "normalized_riot_id_hash ~ '^[0-9a-f]{64}$'",
            name="ck_player_aliases_normalized_riot_id_hash_format",
        ),
        sa.CheckConstraint(
            "last_seen_at >= first_seen_at",
            name="ck_player_aliases_timestamp_order",
        ),
        sa.ForeignKeyConstraint(
            ["player_subject_id"],
            ["player_subjects.player_subject_id"],
            name="fk_player_aliases_player_subject_id_player_subjects",
        ),
        sa.PrimaryKeyConstraint("player_alias_id", name="pk_player_aliases"),
        sa.UniqueConstraint(
            "player_subject_id",
            "routing_region",
            "normalized_riot_id_hash",
            name="uq_player_aliases_subject_region_riot_id_hash",
        ),
    )
    op.create_index(
        "ix_player_aliases_player_subject_id",
        "player_aliases",
        ["player_subject_id"],
        unique=False,
    )

    op.create_table(
        "owner_player_relationships",
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_role", sa.String(length=16), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
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
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="ck_owner_player_relationships_relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "verification_status IN ("
            "'unverified_claim', 'not_applicable', 'rso_verified'"
            ")",
            name="ck_owner_player_relationships_verification_status_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'hidden')",
            name="ck_owner_player_relationships_status_allowed",
        ),
        sa.CheckConstraint(
            "("
            "(relationship_role = 'self' AND verification_status IN ("
            "'unverified_claim', 'rso_verified'"
            ")) OR "
            "(relationship_role = 'observed' AND verification_status = 'not_applicable')"
            ")",
            name="ck_owner_player_relationships_role_verification_allowed",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND hidden_at IS NULL) OR "
            "(status = 'hidden' AND hidden_at IS NOT NULL)",
            name="ck_owner_player_relationships_hidden_status_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(hidden_at IS NULL OR hidden_at >= created_at)",
            name="ck_owner_player_relationships_timestamp_order",
        ),
        sa.ForeignKeyConstraint(
            ["player_subject_id"],
            ["player_subjects.player_subject_id"],
            name="fk_owner_player_relationships_player_subject_id_player_subjects",
        ),
        sa.PrimaryKeyConstraint(
            "relationship_id",
            name="pk_owner_player_relationships",
        ),
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
    )
    op.create_index(
        "ix_owner_player_relationships_player_subject_id",
        "owner_player_relationships",
        ["player_subject_id"],
        unique=False,
    )

    op.create_table(
        "player_link_tasks",
        sa.Column("link_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "task_kind",
            sa.String(length=64),
            server_default=sa.text("'player_link'"),
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("game_name", sa.String(length=64), nullable=False),
        sa.Column("tag_line", sa.String(length=32), nullable=False),
        sa.Column("routing_region", sa.String(length=16), nullable=False),
        sa.Column("relationship_role", sa.String(length=16), nullable=False),
        sa.Column("alias_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'queued'"),
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
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_reason", sa.String(length=64), nullable=True),
        sa.Column("confirmed_game_name", sa.String(length=64), nullable=True),
        sa.Column("confirmed_tag_line", sa.String(length=32), nullable=True),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "task_kind = 'player_link'",
            name="ck_player_link_tasks_task_kind_allowed",
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'",
            name="ck_player_link_tasks_schema_version_allowed",
        ),
        sa.CheckConstraint(
            "routing_region IN ('americas', 'asia', 'europe', 'sea')",
            name="ck_player_link_tasks_routing_region_allowed",
        ),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name="ck_player_link_tasks_relationship_role_allowed",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_player_link_tasks_request_fingerprint_format",
        ),
        sa.CheckConstraint(
            "alias_hash ~ '^[0-9a-f]{64}$'",
            name="ck_player_link_tasks_alias_hash_format",
        ),
        sa.CheckConstraint(
            "terminal_reason IS NULL OR "
            "terminal_reason ~ '^[a-z0-9]+(?:[._-][a-z0-9]+)*$'",
            name="ck_player_link_tasks_terminal_reason_format",
        ),
        sa.CheckConstraint(
            "char_length(btrim(game_name)) BETWEEN 1 AND 64 AND "
            "char_length(btrim(tag_line)) BETWEEN 1 AND 32",
            name="ck_player_link_tasks_riot_id_components_bounded",
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
            name="ck_player_link_tasks_lifecycle_shape",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND "
            "(claimed_at IS NULL OR claimed_at >= created_at) AND "
            "(finished_at IS NULL OR "
            "(claimed_at IS NOT NULL AND finished_at >= claimed_at))",
            name="ck_player_link_tasks_timestamp_order",
        ),
        sa.ForeignKeyConstraint(
            ["player_subject_id"],
            ["player_subjects.player_subject_id"],
            name="fk_player_link_tasks_player_subject_id_player_subjects",
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
        sa.PrimaryKeyConstraint("link_task_id", name="pk_player_link_tasks"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_player_link_tasks_owner_id_idempotency_key",
        ),
    )
    op.create_index(
        "ix_player_link_tasks_claim",
        "player_link_tasks",
        ["status", "created_at", "link_task_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_link_tasks_owner_history",
        "player_link_tasks",
        ["owner_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_player_link_tasks_player_subject_id",
        "player_link_tasks",
        ["player_subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_link_tasks_relationship_id",
        "player_link_tasks",
        ["relationship_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_player_link_tasks_relationship_id",
        table_name="player_link_tasks",
    )
    op.drop_index(
        "ix_player_link_tasks_player_subject_id",
        table_name="player_link_tasks",
    )
    op.drop_index(
        "ix_player_link_tasks_owner_history",
        table_name="player_link_tasks",
    )
    op.drop_index("ix_player_link_tasks_claim", table_name="player_link_tasks")
    op.drop_table("player_link_tasks")

    op.drop_index(
        "ix_owner_player_relationships_player_subject_id",
        table_name="owner_player_relationships",
    )
    op.drop_table("owner_player_relationships")

    op.drop_index("ix_player_aliases_player_subject_id", table_name="player_aliases")
    op.drop_table("player_aliases")

    op.drop_table("player_subjects")
