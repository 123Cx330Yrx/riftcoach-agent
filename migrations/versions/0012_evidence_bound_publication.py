"""Persist the trusted publication mode for review tasks.

Revision ID: 0012_evidence_bound_publication
Revises: 0011_evidence_product_api
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0012_evidence_bound_publication"
down_revision: str | None = "0011_evidence_product_api"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows are deliberately assigned legacy behavior.  The mode is
    # trusted task metadata, never inferred from a report or local files.
    op.add_column(
        "review_tasks",
        sa.Column(
            "publication_mode",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'legacy'"),
        ),
    )
    op.create_check_constraint(
        op.f("ck_review_tasks_publication_mode_allowed"),
        "review_tasks",
        "publication_mode IN ('legacy', 'evidence_bound_v1')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_review_tasks_publication_mode_allowed"),
        "review_tasks",
        type_="check",
    )
    op.drop_column("review_tasks", "publication_mode")
