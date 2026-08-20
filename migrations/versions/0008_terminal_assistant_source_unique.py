"""Add terminal Assistant source-run idempotency.

Revision ID: 0008_terminal_assistant
Revises: 0007_training_plan_progress
Create Date: 2026-08-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0008_terminal_assistant"
down_revision: str | None = "0007_training_plan_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_conversation_messages_assistant_source_run",
        "conversation_messages",
        ["conversation_id", "source_run_id"],
        unique=True,
        postgresql_where=sa.text("role = 'assistant'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_conversation_messages_assistant_source_run",
        table_name="conversation_messages",
    )
