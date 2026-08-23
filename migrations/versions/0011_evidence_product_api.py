"""Add immutable EvidenceBundle snapshot storage for the product API.

Revision ID: 0011_evidence_product_api
Revises: 0010_reliable_runtime_core
Create Date: 2026-08-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0011_evidence_product_api"
down_revision: str | None = "0010_reliable_runtime_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_bundle_snapshots",
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("refresh_id", sa.String(length=128), nullable=False),
        sa.Column("bundle_digest", sa.String(length=64), nullable=False),
        sa.Column("snapshot_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_evidence_bundle_snapshots_revision_positive"),
        ),
        sa.CheckConstraint(
            "refresh_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'",
            name=op.f("ck_evidence_bundle_snapshots_refresh_id_format"),
        ),
        sa.CheckConstraint(
            "bundle_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_evidence_bundle_snapshots_bundle_digest_format"),
        ),
        sa.CheckConstraint(
            "snapshot_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_evidence_bundle_snapshots_snapshot_digest_format"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object' AND "
            "octet_length(payload::text) <= 262144",
            name=op.f("ck_evidence_bundle_snapshots_payload_bound"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "run_id", "owner_id"],
            [
                "review_tasks.task_id",
                "review_tasks.run_id",
                "review_tasks.owner_id",
            ],
            name=op.f("fk_evidence_bundle_snapshots_task_identity"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            name=op.f("pk_evidence_bundle_snapshots"),
        ),
        sa.UniqueConstraint(
            "task_id",
            "revision",
            name=op.f("uq_evidence_bundle_snapshots_task_revision"),
        ),
        sa.UniqueConstraint(
            "task_id",
            "refresh_id",
            name=op.f("uq_evidence_bundle_snapshots_task_refresh"),
        ),
    )
    op.create_index(
        "ix_evidence_bundle_snapshots_owner_run_revision",
        "evidence_bundle_snapshots",
        ["owner_id", "run_id", sa.text("revision DESC")],
        unique=False,
    )
    op.create_index(
        "ix_evidence_bundle_snapshots_task_revision",
        "evidence_bundle_snapshots",
        ["task_id", sa.text("revision DESC")],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION prevent_evidence_bundle_snapshot_update()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'evidence_bundle_snapshot_immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_evidence_bundle_snapshots_no_update
        BEFORE UPDATE ON evidence_bundle_snapshots
        FOR EACH ROW
        EXECUTE FUNCTION prevent_evidence_bundle_snapshot_update()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_evidence_bundle_snapshots_no_update "
        "ON evidence_bundle_snapshots"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_evidence_bundle_snapshot_update()")
    op.drop_index(
        "ix_evidence_bundle_snapshots_task_revision",
        table_name="evidence_bundle_snapshots",
    )
    op.drop_index(
        "ix_evidence_bundle_snapshots_owner_run_revision",
        table_name="evidence_bundle_snapshots",
    )
    op.drop_table("evidence_bundle_snapshots")
