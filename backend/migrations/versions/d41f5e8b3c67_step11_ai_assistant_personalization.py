"""step11_ai_assistant_personalization

Revision ID: d41f5e8b3c67
Revises: c30f4e7b2d56
Create Date: 2026-10-04 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd41f5e8b3c67'
down_revision: Union[str, None] = 'c30f4e7b2d56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Step 11 personalization preferences to user_preferences
    op.add_column(
        'user_preferences',
        sa.Column('assistant_response_style', sa.String(length=50), server_default='concise', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('save_conversation_history', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('use_alarm_history_suggestions', sa.Boolean(), server_default='true', nullable=False)
    )

    # 2. Create assistant_conversations table
    op.create_table(
        'assistant_conversations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), server_default='New Conversation', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assistant_conversations_id', 'assistant_conversations', ['id'])
    op.create_index('ix_assistant_conversations_user_id', 'assistant_conversations', ['user_id'])

    # 3. Create assistant_messages table
    op.create_table(
        'assistant_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['assistant_conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assistant_messages_id', 'assistant_messages', ['id'])
    op.create_index('ix_assistant_messages_conversation_id', 'assistant_messages', ['conversation_id'])
    op.create_index('ix_assistant_messages_user_id', 'assistant_messages', ['user_id'])

    # 4. Create draft_status_enum for PostgreSQL (or fallback for SQLite)
    draft_status_enum = sa.Enum('draft', 'confirmed', 'discarded', name='draft_status_enum')
    transport_mode_enum = sa.Enum('driving', 'transit', 'bicycling', 'walking', name='transport_mode_enum')

    # 5. Create alarm_drafts table
    op.create_table(
        'alarm_drafts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=150), server_default='Smart Alarm Draft', nullable=False),
        sa.Column('destination_text', sa.String(length=500), nullable=False),
        sa.Column('destination_id', sa.Uuid(), nullable=True),
        sa.Column('destination_address', sa.String(length=500), nullable=True),
        sa.Column('destination_lat', sa.Float(), nullable=True),
        sa.Column('destination_lng', sa.Float(), nullable=True),
        sa.Column('arrival_time', sa.Time(), nullable=False),
        sa.Column('arrival_date', sa.Date(), nullable=True),
        sa.Column('preparation_time', sa.Integer(), server_default='30', nullable=False),
        sa.Column('safety_buffer', sa.Integer(), server_default='15', nullable=False),
        sa.Column('transportation_mode', transport_mode_enum, server_default='driving', nullable=False),
        sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('calculated_wake_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('calculated_leave_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_arrival_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('travel_duration_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('traffic_delay_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', draft_status_enum, server_default='draft', nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['assistant_conversations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['destination_id'], ['destinations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alarm_drafts_id', 'alarm_drafts', ['id'])
    op.create_index('ix_alarm_drafts_user_id', 'alarm_drafts', ['user_id'])
    op.create_index('ix_alarm_drafts_conversation_id', 'alarm_drafts', ['conversation_id'])
    op.create_index('ix_alarm_drafts_destination_id', 'alarm_drafts', ['destination_id'])
    op.create_index('ix_alarm_drafts_status', 'alarm_drafts', ['status'])
    op.create_index('ix_alarm_drafts_idempotency_key', 'alarm_drafts', ['idempotency_key'])


def downgrade() -> None:
    op.drop_index('ix_alarm_drafts_idempotency_key', table_name='alarm_drafts')
    op.drop_index('ix_alarm_drafts_status', table_name='alarm_drafts')
    op.drop_index('ix_alarm_drafts_destination_id', table_name='alarm_drafts')
    op.drop_index('ix_alarm_drafts_conversation_id', table_name='alarm_drafts')
    op.drop_index('ix_alarm_drafts_user_id', table_name='alarm_drafts')
    op.drop_index('ix_alarm_drafts_id', table_name='alarm_drafts')
    op.drop_table('alarm_drafts')

    op.drop_index('ix_assistant_messages_user_id', table_name='assistant_messages')
    op.drop_index('ix_assistant_messages_conversation_id', table_name='assistant_messages')
    op.drop_index('ix_assistant_messages_id', table_name='assistant_messages')
    op.drop_table('assistant_messages')

    op.drop_index('ix_assistant_conversations_user_id', table_name='assistant_conversations')
    op.drop_index('ix_assistant_conversations_id', table_name='assistant_conversations')
    op.drop_table('assistant_conversations')

    sa.Enum(name='draft_status_enum').drop(op.get_bind(), checkfirst=True)

    op.drop_column('user_preferences', 'use_alarm_history_suggestions')
    op.drop_column('user_preferences', 'save_conversation_history')
    op.drop_column('user_preferences', 'assistant_response_style')
