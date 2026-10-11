"""Initial schema with all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_admin', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    )

    # Teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_teams_owner', 'teams', ['owner_id'])

    # Team members table
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('role', sa.String(20), default='member', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_team_members_team_user', 'team_members', ['team_id', 'user_id'])

    # Shares table
    op.create_table(
        'shares',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('resource_type', sa.String(20), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('shared_with_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('shared_with_team_id', sa.String(36), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('permission', sa.String(20), default='read', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_shares_resource', 'shares', ['resource_type', 'resource_id'])
    op.create_index('ix_shares_owner', 'shares', ['owner_id'])
    op.create_index('ix_shares_user', 'shares', ['shared_with_user_id'])
    op.create_index('ix_shares_team', 'shares', ['shared_with_team_id'])

    # Usage events table
    op.create_table(
        'usage_events',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(20), nullable=True),
        sa.Column('token_count', sa.Integer, default=0, nullable=True),
        sa.Column('latency_ms', sa.Float, nullable=True),
        sa.Column('success', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_usage_events_user', 'usage_events', ['user_id'])
    op.create_index('ix_usage_events_type', 'usage_events', ['event_type'])
    op.create_index('ix_usage_events_created', 'usage_events', ['created_at'])

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('owner_id', sa.String(255), nullable=False, index=True),
        sa.Column('filename', sa.String(255), nullable=False, index=True),
        sa.Column('version', sa.Integer, default=1, nullable=False),
        sa.Column('is_latest', sa.Boolean, default=True, nullable=False),
        sa.Column('chunk_count', sa.Integer, default=0, nullable=False),
        sa.Column('text_length', sa.Integer, default=0, nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_documents_owner_filename', 'documents', ['owner_id', 'filename'])
    op.create_index('ix_documents_owner_latest', 'documents', ['owner_id', 'is_latest'])

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True, index=True),
        sa.Column('owner_id', sa.String(255), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_conversations_owner_created', 'conversations', ['owner_id', 'created_at'])

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_messages_conversation_timestamp', 'messages', ['conversation_id', 'timestamp'])


def downgrade() -> None:
    op.drop_index('ix_messages_conversation_timestamp')
    op.drop_table('messages')
    op.drop_index('ix_conversations_owner_created')
    op.drop_table('conversations')
    op.drop_index('ix_documents_owner_latest')
    op.drop_index('ix_documents_owner_filename')
    op.drop_table('documents')
    op.drop_index('ix_usage_events_created')
    op.drop_index('ix_usage_events_type')
    op.drop_index('ix_usage_events_user')
    op.drop_table('usage_events')
    op.drop_index('ix_shares_team')
    op.drop_index('ix_shares_user')
    op.drop_index('ix_shares_owner')
    op.drop_index('ix_shares_resource')
    op.drop_table('shares')
    op.drop_index('ix_team_members_team_user')
    op.drop_table('team_members')
    op.drop_index('ix_teams_owner')
    op.drop_table('teams')
    op.drop_table('users')
