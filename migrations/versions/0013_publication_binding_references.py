"""Persist body-free evidence publication binding references.

Revision ID: 0013_publication_binding_references
Revises: 0012_evidence_bound_publication
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0013_publication_binding_references"
down_revision: str | None = "0012_evidence_bound_publication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_tasks",
        sa.Column(
            "publication_reference",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column("summary_digest", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column(
            "first_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "review_tasks",
        sa.Column("first_snapshot_digest", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_publication_reference_shape"),
        "review_tasks",
        "publication_reference IS NULL OR "
        "(jsonb_typeof(publication_reference) = 'object' AND "
        "octet_length(publication_reference::text) <= 4096)",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_summary_digest_format"),
        "review_tasks",
        "summary_digest IS NULL OR summary_digest ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_first_snapshot_digest_format"),
        "review_tasks",
        "first_snapshot_digest IS NULL OR "
        "first_snapshot_digest ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_first_snapshot_binding_shape"),
        "review_tasks",
        "(first_snapshot_id IS NULL AND first_snapshot_digest IS NULL) OR "
        "(first_snapshot_id IS NOT NULL AND first_snapshot_digest IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_legacy_publication_fields_empty"),
        "review_tasks",
        "publication_mode = 'evidence_bound_v1' OR "
        "(publication_reference IS NULL AND summary_digest IS NULL AND "
        "first_snapshot_id IS NULL AND first_snapshot_digest IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_review_tasks_legacy_publication_fields_empty"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_first_snapshot_binding_shape"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_first_snapshot_digest_format"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_summary_digest_format"),
        "review_tasks",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_tasks_publication_reference_shape"),
        "review_tasks",
        type_="check",
    )
    op.drop_column("review_tasks", "first_snapshot_digest")
    op.drop_column("review_tasks", "first_snapshot_id")
    op.drop_column("review_tasks", "summary_digest")
    op.drop_column("review_tasks", "publication_reference")

