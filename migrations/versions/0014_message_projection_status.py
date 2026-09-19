"""Add durable post-commit message projection status."""
from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0014_message_projection_status"
down_revision: str | None = "0013_publication_bindings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("review_tasks", sa.Column("message_projection_status", sa.String(16), nullable=False, server_default=sa.text("'not_required'")))
    op.create_check_constraint(op.f("ck_review_tasks_message_projection_status_allowed"), "review_tasks", "message_projection_status IN ('not_required', 'pending', 'completed')")

def downgrade() -> None:
    op.drop_constraint(op.f("ck_review_tasks_message_projection_status_allowed"), "review_tasks", type_="check")
    op.drop_column("review_tasks", "message_projection_status")
