"""Create typed Preference, Player Profile, and Review Memory targets.

Revision ID: 0006_typed_memory_targets
Revises: 0005_memory_candidates
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0006_typed_memory_targets"
down_revision: str | None = "0005_memory_candidates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> list[sa.Column]:
    return [
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("source_conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_role", sa.String(length=16), nullable=False),
        sa.Column("memory_key", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supersedes_record_id", postgresql.UUID(as_uuid=True), nullable=True),
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
    ]


def _checks(table_name: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            "schema_version = '1.0'",
            name=op.f(f"ck_{table_name}_schema_version_allowed"),
        ),
        sa.CheckConstraint(
            "relationship_role IN ('self', 'observed')",
            name=op.f(f"ck_{table_name}_relationship_role_allowed"),
        ),
        sa.CheckConstraint(
            "version >= 1 AND version <= 2147483647",
            name=op.f(f"ck_{table_name}_version_range"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded', 'retired')",
            name=op.f(f"ck_{table_name}_status_allowed"),
        ),
        sa.CheckConstraint(
            "payload_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f(f"ck_{table_name}_payload_digest_format"),
        ),
        sa.CheckConstraint(
            "octet_length(payload::text) <= 6144",
            name=op.f(f"ck_{table_name}_payload_storage_bound"),
        ),
        sa.CheckConstraint(
            "(version = 1 AND supersedes_record_id IS NULL) OR "
            "(version > 1 AND supersedes_record_id IS NOT NULL)",
            name=op.f(f"ck_{table_name}_supersedes_shape"),
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name=op.f(f"ck_{table_name}_timestamp_order"),
        ),
    ]


def _candidate_fk(name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
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
        name=name,
    )


def _relationship_fk(name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["owner_id", "relationship_id", "player_subject_id", "relationship_role"],
        [
            "owner_player_relationships.owner_id",
            "owner_player_relationships.relationship_id",
            "owner_player_relationships.player_subject_id",
            "owner_player_relationships.relationship_role",
        ],
        name=name,
    )


def upgrade() -> None:
    op.create_table(
        "memory_preferences",
        *_columns(),
        sa.PrimaryKeyConstraint("record_id", name="pk_memory_preferences"),
        sa.UniqueConstraint(
            "source_candidate_id",
            name="uq_memory_preferences_source_candidate",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "memory_key",
            "version",
            name="uq_memory_preferences_version",
        ),
        _candidate_fk("fk_memory_preferences_candidate_identity"),
        sa.ForeignKeyConstraint(
            ["supersedes_record_id"],
            ["memory_preferences.record_id"],
            name="fk_memory_preferences_supersedes",
        ),
        *_checks("memory_preferences"),
        sa.CheckConstraint(
            "relationship_role = 'self'",
            name=op.f("ck_memory_preferences_self_only"),
        ),
        sa.CheckConstraint(
            "memory_key = 'report_language'",
            name=op.f("ck_memory_preferences_memory_key_allowed"),
        ),
    )
    op.create_index(
        "ix_memory_preferences_owner_history",
        "memory_preferences",
        ["owner_id", "memory_key", sa.text("version DESC")],
    )
    op.create_index(
        "uq_memory_preferences_active",
        "memory_preferences",
        ["owner_id", "memory_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "player_profiles",
        *_columns(),
        sa.PrimaryKeyConstraint("record_id", name="pk_player_profiles"),
        sa.UniqueConstraint(
            "source_candidate_id",
            name="uq_player_profiles_source_candidate",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "memory_key",
            "version",
            name="uq_player_profiles_version",
        ),
        _candidate_fk("fk_player_profiles_candidate_identity"),
        _relationship_fk("fk_player_profiles_relationship_identity"),
        sa.ForeignKeyConstraint(
            ["supersedes_record_id"],
            ["player_profiles.record_id"],
            name="fk_player_profiles_supersedes",
        ),
        *_checks("player_profiles"),
        sa.CheckConstraint(
            "relationship_role = 'self'",
            name=op.f("ck_player_profiles_self_only"),
        ),
        sa.CheckConstraint(
            "memory_key IN ('main_role', 'champion_pool')",
            name=op.f("ck_player_profiles_memory_key_allowed"),
        ),
    )
    op.create_index(
        "ix_player_profiles_owner_history",
        "player_profiles",
        ["owner_id", "relationship_id", "memory_key", sa.text("version DESC")],
    )
    op.create_index(
        "uq_player_profiles_active",
        "player_profiles",
        ["owner_id", "relationship_id", "player_subject_id", "memory_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "review_memories",
        *_columns(),
        sa.PrimaryKeyConstraint("record_id", name="pk_review_memories"),
        sa.UniqueConstraint(
            "source_candidate_id",
            name="uq_review_memories_source_candidate",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            "memory_key",
            "version",
            name="uq_review_memories_version",
        ),
        _candidate_fk("fk_review_memories_candidate_identity"),
        _relationship_fk("fk_review_memories_relationship_identity"),
        sa.ForeignKeyConstraint(
            ["supersedes_record_id"],
            ["review_memories.record_id"],
            name="fk_review_memories_supersedes",
        ),
        *_checks("review_memories"),
        sa.CheckConstraint(
            "memory_key IN ('review_summary', 'observation_note', 'public_trend')",
            name=op.f("ck_review_memories_memory_key_allowed"),
        ),
        sa.CheckConstraint(
            "relationship_role <> 'observed' OR "
            "memory_key IN ('observation_note', 'public_trend')",
            name=op.f("ck_review_memories_observed_key_allowed"),
        ),
    )
    op.create_index(
        "ix_review_memories_owner_history",
        "review_memories",
        [
            "owner_id",
            "relationship_id",
            "relationship_role",
            "memory_key",
            sa.text("version DESC"),
        ],
    )
    op.create_index(
        "uq_review_memories_active",
        "review_memories",
        [
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
            "memory_key",
        ],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    _create_target_guard_functions()
    for table_name in ("memory_preferences", "player_profiles", "review_memories"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_validate_insert
            BEFORE INSERT ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION riftcoach_validate_typed_memory_target()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_guard_update
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION riftcoach_guard_typed_memory_update()
            """
        )


def _create_target_guard_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION riftcoach_validate_typed_memory_target()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            source memory_candidates%ROWTYPE;
            prior jsonb;
        BEGIN
            SELECT * INTO source
            FROM memory_candidates
            WHERE candidate_id = NEW.source_candidate_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'typed_memory_source_candidate_missing' USING ERRCODE = '23503';
            END IF;
            IF source.status <> 'pending' OR
               ROW(source.owner_id, source.conversation_id, source.relationship_id,
                   source.player_subject_id, source.relationship_role) IS DISTINCT FROM
               ROW(NEW.owner_id, NEW.source_conversation_id, NEW.relationship_id,
                   NEW.player_subject_id, NEW.relationship_role) THEN
                RAISE EXCEPTION 'typed_memory_source_identity_invalid' USING ERRCODE = '23514';
            END IF;
            IF TG_TABLE_NAME = 'memory_preferences' AND NOT (
                source.candidate_kind = 'owner_preference' AND
                source.target_scope = 'owner_global' AND source.operation = 'set' AND
                source.memory_key = NEW.memory_key AND source.relationship_role = 'self'
            ) THEN
                RAISE EXCEPTION 'typed_memory_preference_source_invalid' USING ERRCODE = '23514';
            ELSIF TG_TABLE_NAME = 'player_profiles' AND NOT (
                source.candidate_kind = 'player_profile' AND
                source.target_scope = 'owner_player' AND source.operation = 'set' AND
                source.memory_key = NEW.memory_key AND source.relationship_role = 'self'
            ) THEN
                RAISE EXCEPTION 'typed_memory_profile_source_invalid' USING ERRCODE = '23514';
            ELSIF TG_TABLE_NAME = 'review_memories' AND NOT (
                source.candidate_kind = 'review_memory' AND
                source.target_scope = 'owner_player' AND source.operation = 'append' AND
                source.memory_key = NEW.memory_key AND
                source.relationship_role = NEW.relationship_role
            ) THEN
                RAISE EXCEPTION 'typed_memory_review_source_invalid' USING ERRCODE = '23514';
            END IF;

            IF NEW.version > 1 THEN
                EXECUTE format(
                    'SELECT to_jsonb(target) FROM %I target WHERE record_id = $1',
                    TG_TABLE_NAME
                ) INTO prior USING NEW.supersedes_record_id;
                IF prior IS NULL OR prior->>'status' <> 'superseded' OR
                   (prior->>'version')::integer <> NEW.version - 1 OR
                   prior->>'owner_id' <> NEW.owner_id OR
                   prior->>'memory_key' <> NEW.memory_key THEN
                    RAISE EXCEPTION 'typed_memory_supersedes_chain_invalid' USING ERRCODE = '23514';
                END IF;
                IF TG_TABLE_NAME <> 'memory_preferences' AND (
                    prior->>'relationship_id' <> NEW.relationship_id::text OR
                    prior->>'player_subject_id' <> NEW.player_subject_id::text
                ) THEN
                    RAISE EXCEPTION 'typed_memory_supersedes_identity_invalid' USING ERRCODE = '23514';
                END IF;
                IF TG_TABLE_NAME = 'review_memories' AND
                   prior->>'relationship_role' <> NEW.relationship_role THEN
                    RAISE EXCEPTION 'typed_memory_supersedes_role_invalid' USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION riftcoach_guard_typed_memory_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF ROW(
                NEW.record_id, NEW.schema_version, NEW.owner_id,
                NEW.source_conversation_id, NEW.relationship_id,
                NEW.player_subject_id, NEW.relationship_role, NEW.memory_key,
                NEW.version, NEW.payload, NEW.payload_sha256,
                NEW.source_candidate_id, NEW.supersedes_record_id, NEW.created_at
            ) IS DISTINCT FROM ROW(
                OLD.record_id, OLD.schema_version, OLD.owner_id,
                OLD.source_conversation_id, OLD.relationship_id,
                OLD.player_subject_id, OLD.relationship_role, OLD.memory_key,
                OLD.version, OLD.payload, OLD.payload_sha256,
                OLD.source_candidate_id, OLD.supersedes_record_id, OLD.created_at
            ) THEN
                RAISE EXCEPTION 'typed_memory_identity_or_payload_immutable' USING ERRCODE = '23514';
            END IF;
            IF OLD.status <> 'active' OR NEW.status NOT IN ('superseded', 'retired') THEN
                RAISE EXCEPTION 'typed_memory_invalid_transition' USING ERRCODE = '23514';
            END IF;
            IF NEW.updated_at < OLD.updated_at THEN
                RAISE EXCEPTION 'typed_memory_timestamp_regression' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )


def downgrade() -> None:
    for table_name in ("review_memories", "player_profiles", "memory_preferences"):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table_name}_guard_update ON {table_name}"
        )
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table_name}_validate_insert ON {table_name}"
        )
    op.execute("DROP FUNCTION IF EXISTS riftcoach_guard_typed_memory_update()")
    op.execute("DROP FUNCTION IF EXISTS riftcoach_validate_typed_memory_target()")

    op.drop_index("uq_review_memories_active", table_name="review_memories")
    op.drop_index("ix_review_memories_owner_history", table_name="review_memories")
    op.drop_table("review_memories")
    op.drop_index("uq_player_profiles_active", table_name="player_profiles")
    op.drop_index("ix_player_profiles_owner_history", table_name="player_profiles")
    op.drop_table("player_profiles")
    op.drop_index("uq_memory_preferences_active", table_name="memory_preferences")
    op.drop_index("ix_memory_preferences_owner_history", table_name="memory_preferences")
    op.drop_table("memory_preferences")
