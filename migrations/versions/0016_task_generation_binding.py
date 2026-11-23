"""Pin a server-selected generation contract at creation; old tasks stay NULL."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = '0016_task_generation_binding'
down_revision = '0015_task_continuation'
branch_labels = depends_on = None


def upgrade():
    op.add_column('review_tasks', sa.Column('generation_binding', postgresql.JSONB(none_as_null=True)))


def downgrade():
    # Emit the same protection in online migrations and offline SQL scripts.
    # Hold a table lock until the transaction drops the column so a concurrent
    # task creator cannot add a pin between this check and DROP COLUMN.
    op.execute('LOCK TABLE review_tasks IN ACCESS EXCLUSIVE MODE')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM review_tasks WHERE generation_binding IS NOT NULL) THEN
            RAISE EXCEPTION 'cannot discard persisted task generation bindings';
        END IF;
    END $$""")
    op.drop_column('review_tasks', 'generation_binding')
