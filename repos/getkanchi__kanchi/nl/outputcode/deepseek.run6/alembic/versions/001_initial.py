"""initial migration

Revision ID: 001
Revises: 
Create Date: 2023-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('args', sa.JSON(), nullable=True),
        sa.Column('kwargs', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('worker', sa.String(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('traceback', sa.String(), nullable=True),
        sa.Column('exception', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index('ix_tasks_name', 'tasks', ['name'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_task_id', 'tasks', ['task_id'])

    op.create_table('workers',
        sa.Column('hostname', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('concurrency', sa.Integer(), nullable=True),
        sa.Column('queues', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('hostname')
    )

    op.create_table('daily_stats',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_tasks', sa.Integer(), nullable=True),
        sa.Column('succeeded', sa.Integer(), nullable=True),
        sa.Column('failed', sa.Integer(), nullable=True),
        sa.Column('retried', sa.Integer(), nullable=True),
        sa.Column('avg_runtime', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_daily_stats_date', 'date')
    )

def downgrade():
    op.drop_table('daily_stats')
    op.drop_table('workers')
    op.drop_index('ix_tasks_task_id', table_name='tasks')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_name', table_name='tasks')
    op.drop_table('tasks')

