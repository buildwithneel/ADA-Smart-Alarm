"""step8_traffic_recalculation

Revision ID: a18f2d5e9b34
Revises: f27a4b8c9d10
Create Date: 2026-10-02 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a18f2d5e9b34'
down_revision: Union[str, None] = 'f27a4b8c9d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Step 8 Dynamic Recalculation columns to alarms
    op.add_column(
        'alarms',
        sa.Column('schedule_version', sa.Integer(), server_default='1', nullable=False)
    )
    op.add_column(
        'alarms',
        sa.Column('last_route_refresh_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('last_schedule_change_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('schedule_change_reason', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('route_freshness_state', sa.String(length=50), server_default='fresh', nullable=False)
    )

    # 2. Add composite index for upcoming alarm refresh queries
    op.create_index(
        'ix_alarms_eligible_refresh',
        'alarms',
        ['enabled', 'status', 'calculated_leave_time'],
        unique=False,
    )

    # 3. Create alarm_schedule_changes audit table
    op.create_table(
        'alarm_schedule_changes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('alarm_id', sa.Uuid(), nullable=False),
        sa.Column('previous_wake_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('new_wake_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_leave_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('new_leave_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_planned_arrival', sa.DateTime(timezone=True), nullable=True),
        sa.Column('new_planned_arrival', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_travel_minutes', sa.Integer(), nullable=True),
        sa.Column('new_travel_minutes', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('schedule_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['alarm_id'], ['alarms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_alarm_schedule_changes_id'),
        'alarm_schedule_changes',
        ['id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_alarm_schedule_changes_alarm_id'),
        'alarm_schedule_changes',
        ['alarm_id'],
        unique=False,
    )
    op.create_index(
        'ix_alarm_schedule_changes_alarm_created',
        'alarm_schedule_changes',
        ['alarm_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_alarm_schedule_changes_alarm_created', table_name='alarm_schedule_changes')
    op.drop_index(op.f('ix_alarm_schedule_changes_alarm_id'), table_name='alarm_schedule_changes')
    op.drop_index(op.f('ix_alarm_schedule_changes_id'), table_name='alarm_schedule_changes')
    op.drop_table('alarm_schedule_changes')

    op.drop_index('ix_alarms_eligible_refresh', table_name='alarms')
    op.drop_column('alarms', 'route_freshness_state')
    op.drop_column('alarms', 'schedule_change_reason')
    op.drop_column('alarms', 'last_schedule_change_at')
    op.drop_column('alarms', 'last_route_refresh_at')
    op.drop_column('alarms', 'schedule_version')
