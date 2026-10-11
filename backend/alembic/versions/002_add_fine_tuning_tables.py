"""Add fine-tuning job tracking tables for Phase 10.

Revision ID: 002_add_fine_tuning_tables
Revises: 001_initial_schema
Create Date: 2026-10-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_fine_tuning_tables'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create fine_tuning_jobs table
    op.create_table(
        'fine_tuning_jobs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('owner_id', sa.String(255), nullable=False),
        sa.Column('job_name', sa.String(255), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('base_model', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('dataset_source', sa.String(255), nullable=False, server_default='both'),
        sa.Column('document_ids', sa.JSON(), nullable=True),
        sa.Column('training_params', sa.JSON(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('external_job_id', sa.String(255), nullable=True),
        sa.Column('artifact_path', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fine_tuning_jobs_owner', 'fine_tuning_jobs', ['owner_id'])
    op.create_index('ix_fine_tuning_jobs_status', 'fine_tuning_jobs', ['status'])
    op.create_index('ix_fine_tuning_jobs_active', 'fine_tuning_jobs', ['owner_id', 'is_active'])

    # Create training_examples table
    op.create_table(
        'training_examples',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('example_type', sa.String(50), nullable=False),
        sa.Column('input_text', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=True),
        sa.Column('source_document_id', sa.String(36), nullable=True),
        sa.Column('source_conversation_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['fine_tuning_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_training_examples_job', 'training_examples', ['job_id'])
    op.create_index('ix_training_examples_type', 'training_examples', ['example_type'])

    # Create training_metrics table
    op.create_table(
        'training_metrics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('epoch', sa.Integer(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['fine_tuning_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_training_metrics_job_epoch', 'training_metrics', ['job_id', 'epoch'])


def downgrade():
    op.drop_index('ix_training_metrics_job_epoch', table_name='training_metrics')
    op.drop_table('training_metrics')
    op.drop_index('ix_training_examples_type', table_name='training_examples')
    op.drop_index('ix_training_examples_job', table_name='training_examples')
    op.drop_table('training_examples')
    op.drop_index('ix_fine_tuning_jobs_active', table_name='fine_tuning_jobs')
    op.drop_index('ix_fine_tuning_jobs_status', table_name='fine_tuning_jobs')
    op.drop_index('ix_fine_tuning_jobs_owner', table_name='fine_tuning_jobs')
    op.drop_table('fine_tuning_jobs')
