"""step9_notifications_delivery

Revision ID: b29e3f6a1c45
Revises: a18f2d5e9b34
Create Date: 2026-10-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'b29e3f6a1c45'
down_revision: Union[str, None] = 'a18f2d5e9b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add notification preference fields to user_preferences
    op.add_column(
        'user_preferences',
        sa.Column('wake_alarm_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('departure_reminder_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('departure_reminder_lead_minutes', sa.Integer(), server_default='10', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('schedule_change_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('traffic_change_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('in_app_enabled', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'user_preferences',
        sa.Column('web_push_enabled', sa.Boolean(), server_default='true', nullable=False)
    )

    # 2. Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('alarm_id', sa.Uuid(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('channel', sa.String(length=50), server_default='ALL', nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('schedule_version', sa.Integer(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=160), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON().with_variant(JSONB, 'postgresql'), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['alarm_id'], ['alarms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_alarm_id'), 'notifications', ['alarm_id'], unique=False)
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)
    op.create_index(op.f('ix_notifications_scheduled_for'), 'notifications', ['scheduled_for'], unique=False)
    op.create_index(op.f('ix_notifications_idempotency_key'), 'notifications', ['idempotency_key'], unique=True)
    op.create_index('ix_notifications_user_id_status', 'notifications', ['user_id', 'status'], unique=False)
    op.create_index('ix_notifications_scheduled_for_status', 'notifications', ['scheduled_for', 'status'], unique=False)

    # 3. Create push_subscriptions table
    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh_key', sa.Text(), nullable=False),
        sa.Column('auth_key', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint')
    )
    op.create_index(op.f('ix_push_subscriptions_id'), 'push_subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_push_subscriptions_user_id'), 'push_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_push_subscriptions_endpoint'), 'push_subscriptions', ['endpoint'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_push_subscriptions_endpoint'), table_name='push_subscriptions')
    op.drop_index(op.f('ix_push_subscriptions_user_id'), table_name='push_subscriptions')
    op.drop_index(op.f('ix_push_subscriptions_id'), table_name='push_subscriptions')
    op.drop_table('push_subscriptions')

    op.drop_index('ix_notifications_scheduled_for_status', table_name='notifications')
    op.drop_index('ix_notifications_user_id_status', table_name='notifications')
    op.drop_index(op.f('ix_notifications_idempotency_key'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_scheduled_for'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_alarm_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')

    op.drop_column('user_preferences', 'web_push_enabled')
    op.drop_column('user_preferences', 'in_app_enabled')
    op.drop_column('user_preferences', 'traffic_change_enabled')
    op.drop_column('user_preferences', 'schedule_change_enabled')
    op.drop_column('user_preferences', 'departure_reminder_lead_minutes')
    op.drop_column('user_preferences', 'departure_reminder_enabled')
    op.drop_column('user_preferences', 'wake_alarm_enabled')
