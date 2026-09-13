"""initial migration

Revision ID: 001
Revises: None
Create Date: 2023-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('PENDING','STARTED','SUCCESS','FAILURE','RETRY','REVOKED','ORPHAN', name='taskstatus'), nullable=True),
        sa.Column('args', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('kwargs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('worker', sa.String(255), nullable=True),
        sa.Column('date_done', sa.DateTime(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index(op.f('ix_tasks_created_at'), 'tasks', ['created_at'], unique=False)
    op.create_index(op.f('ix_tasks_name'), 'tasks', ['name'], unique=False)
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
    op.create_index(op.f('ix_tasks_task_id'), 'tasks', ['task_id'], unique=True)
    op.create_index(op.f('ix_tasks_worker'), 'tasks', ['worker'], unique=False)

    op.create_table('workers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hostname', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('ONLINE','OFFLINE', name='workerstatus'), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname')
    )
    op.create_index(op.f('ix_workers_hostname'), 'workers', ['hostname'], unique=True)

    op.create_table('daily_task_statistics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('succeeded', sa.Integer(), nullable=True),
        sa.Column('failed', sa.Integer(), nullable=True),
        sa.Column('retried', sa.Integer(), nullable=True),
        sa.Column('pending', sa.Integer(), nullable=True),
        sa.Column('revoked', sa.Integer(), nullable=True),
        sa.Column('orphan', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index(op.f('ix_daily_task_statistics_date'), 'daily_task_statistics', ['date'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_daily_task_statistics_date'), table_name='daily_task_statistics')
    op.drop_table('daily_task_statistics')
    op.drop_index(op.f('ix_workers_hostname'), table_name='workers')
    op.drop_table('workers')
    op.drop_index(op.f('ix_tasks_worker'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_task_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_name'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_created_at'), table_name='tasks')
    op.drop_table('tasks')
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS workerstatus")

