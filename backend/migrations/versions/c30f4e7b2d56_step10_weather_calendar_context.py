"""step10_weather_calendar_context

Revision ID: c30f4e7b2d56
Revises: b29e3f6a1c45
Create Date: 2026-10-04 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c30f4e7b2d56'
down_revision: Union[str, None] = 'b29e3f6a1c45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add context and calendar preferences to user_preferences
    op.add_column(
        'user_preferences',
        sa.Column('weather_buffer_enabled', sa.Boolean(), server_default='false', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('weather_buffer_mode', sa.String(length=50), server_default='informational_only', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('weather_buffer_minutes', sa.Integer(), server_default='10', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('weather_alerts_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('calendar_sync_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('calendar_auto_reschedule', sa.Boolean(), server_default='false', nullable=False)
    )

    # 2. Add weather & calendar context fields to alarms
    op.add_column(
        'alarms',
        sa.Column('weather_buffer_minutes', sa.Integer(), server_default='0', nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('weather_condition_snapshot', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('calendar_event_id', sa.String(length=255), nullable=True)
    )
    op.create_index('ix_alarms_calendar_event_id', 'alarms', ['calendar_event_id'], unique=False)

    # 3. Create calendar_connections table
    op.create_table(
        'calendar_connections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=50), server_default='google', nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('encrypted_access_token', sa.String(length=1024), nullable=False),
        sa.Column('encrypted_refresh_token', sa.String(length=1024), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(length=50), server_default='idle', nullable=False),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_calendar_connections_id', 'calendar_connections', ['id'], unique=False)
    op.create_index('ix_calendar_connections_user_id', 'calendar_connections', ['user_id'], unique=False)

    # 4. Create calendar_events table
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('connection_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('alarm_id', sa.Uuid(), nullable=True),
        sa.Column('external_event_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(length=50), server_default='UTC', nullable=False),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('resolved_latitude', sa.Float(), nullable=True),
        sa.Column('resolved_longitude', sa.Float(), nullable=True),
        sa.Column('all_day', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='confirmed', nullable=False),
        sa.Column('source_provider', sa.String(length=50), server_default='google', nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_link', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['connection_id'], ['calendar_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['alarm_id'], ['alarms.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_calendar_events_id', 'calendar_events', ['id'], unique=False)
    op.create_index('ix_calendar_events_connection_id', 'calendar_events', ['connection_id'], unique=False)
    op.create_index('ix_calendar_events_user_id', 'calendar_events', ['user_id'], unique=False)
    op.create_index('ix_calendar_events_alarm_id', 'calendar_events', ['alarm_id'], unique=False)
    op.create_index('ix_calendar_events_external_event_id', 'calendar_events', ['external_event_id'], unique=False)
    op.create_index('ix_calendar_events_start_time', 'calendar_events', ['start_time'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_calendar_events_start_time', table_name='calendar_events')
    op.drop_index('ix_calendar_events_external_event_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_alarm_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_user_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_connection_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_id', table_name='calendar_events')
    op.drop_table('calendar_events')

    op.drop_index('ix_calendar_connections_user_id', table_name='calendar_connections')
    op.drop_index('ix_calendar_connections_id', table_name='calendar_connections')
    op.drop_table('calendar_connections')

    op.drop_index('ix_alarms_calendar_event_id', table_name='alarms')
    op.drop_column('alarms', 'calendar_event_id')
    op.drop_column('alarms', 'weather_condition_snapshot')
    op.drop_column('alarms', 'weather_buffer_minutes')

    op.drop_column('user_preferences', 'calendar_auto_reschedule')
    op.drop_column('user_preferences', 'calendar_sync_enabled')
    op.drop_column('user_preferences', 'weather_alerts_enabled')
    op.drop_column('user_preferences', 'weather_buffer_minutes')
    op.drop_column('user_preferences', 'weather_buffer_mode')
    op.drop_column('user_preferences', 'weather_buffer_enabled')
