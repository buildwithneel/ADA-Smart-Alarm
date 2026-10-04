"""step7_smart_alarm_engine

Revision ID: f27a4b8c9d10
Revises: e16e1e3b2cb1
Create Date: 2026-10-02 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f27a4b8c9d10'
down_revision: Union[str, None] = 'e16e1e3b2cb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

alarm_status_enum = sa.Enum(
    'draft', 'scheduled', 'active', 'disabled', 'expired', 'completed', 'cancelled', 'error',
    name='alarm_status_enum'
)


def upgrade() -> None:
    # 1. Create alarm_status_enum type if PostgreSQL
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        alarm_status_enum.create(bind, checkfirst=True)

    # 2. Add columns to alarms table
    op.add_column(
        'alarms',
        sa.Column(
            'status',
            alarm_status_enum,
            server_default='scheduled',
            nullable=False,
        )
    )
    op.add_column(
        'alarms',
        sa.Column('planned_arrival_time', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False)
    )
    op.add_column(
        'alarms',
        sa.Column('calculation_version', sa.String(length=30), server_default='eta-v1', nullable=False)
    )
    op.add_column(
        'alarms',
        sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('origin_lat', sa.Float(), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('origin_lng', sa.Float(), nullable=True)
    )
    op.add_column(
        'alarms',
        sa.Column('origin_address', sa.String(length=500), nullable=True)
    )

    # 3. Create indexes
    op.create_index(op.f('ix_alarms_status'), 'alarms', ['status'], unique=False)
    op.create_index('ix_alarms_user_id_status', 'alarms', ['user_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_alarms_user_id_status', table_name='alarms')
    op.drop_index(op.f('ix_alarms_status'), table_name='alarms')
    op.drop_column('alarms', 'origin_address')
    op.drop_column('alarms', 'origin_lng')
    op.drop_column('alarms', 'origin_lat')
    op.drop_column('alarms', 'last_calculated_at')
    op.drop_column('alarms', 'calculation_version')
    op.drop_column('alarms', 'timezone')
    op.drop_column('alarms', 'planned_arrival_time')
    op.drop_column('alarms', 'status')

    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        alarm_status_enum.drop(bind, checkfirst=True)
