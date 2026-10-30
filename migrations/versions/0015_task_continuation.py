"""Persist candidate session pins without changing legacy event payloads."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0015_task_continuation"
down_revision = "0014_message_projection_status"
branch_labels = depends_on = None

OLD = ("event_kind IN ('snapshot_imported', 'created', 'claimed', 'heartbeat', "
       "'checkpointed', 'execution_started', 'cancel_requested', 'recovery_requeued', "
       "'recovery_required', 'succeeded', 'failed', 'cancelled', 'reconciled')")
NEW = OLD[:-1] + ", 'continuation_resumed')"


def upgrade():
    op.add_column("review_tasks", sa.Column("continuation_reference", postgresql.JSONB(none_as_null=True)))
    op.drop_constraint(op.f("ck_review_task_events_event_kind_allowed"), "review_task_events", type_="check")
    op.create_check_constraint(op.f("ck_review_task_events_event_kind_allowed"), "review_task_events", NEW)


def downgrade():
    # A database with resumed tasks cannot silently discard their history.
    op.drop_constraint(op.f("ck_review_task_events_event_kind_allowed"), "review_task_events", type_="check")
    op.create_check_constraint(op.f("ck_review_task_events_event_kind_allowed"), "review_task_events", OLD)
    op.drop_column("review_tasks", "continuation_reference")
