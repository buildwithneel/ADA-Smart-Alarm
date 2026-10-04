"""step12_production_indexes

Revision ID: e52a6f9c4d78
Revises: d41f5e8b3c67
Create Date: 2026-10-04 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e52a6f9c4d78'
down_revision: Union[str, None] = 'd41f5e8b3c67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Index on alarms.calculated_leave_time for fast upcoming alarm evaluation sweep
    op.create_index(
        'ix_alarms_calculated_leave_time',
        'alarms',
        ['calculated_leave_time'],
        unique=False
    )

    # 2. Composite index on alarms(user_id, status) for filtered user alarm lists
    op.create_index(
        'ix_alarms_user_id_status',
        'alarms',
        ['user_id', 'status'],
        unique=False
    )

    # 3. Composite index on alarms(enabled, calculated_wake_time) for scheduler sorting
    op.create_index(
        'ix_alarms_enabled_wake_time',
        'alarms',
        ['enabled', 'calculated_wake_time'],
        unique=False
    )

    # 4. Composite index on destinations(user_id, is_favorite) for fast favorite lookups
    op.create_index(
        'ix_destinations_user_id_favorite',
        'destinations',
        ['user_id', 'is_favorite'],
        unique=False
    )

    # 5. Composite index on alarm_drafts(user_id, status)
    op.create_index(
        'ix_alarm_drafts_user_id_status',
        'alarm_drafts',
        ['user_id', 'status'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_alarm_drafts_user_id_status', table_name='alarm_drafts')
    op.drop_index('ix_destinations_user_id_favorite', table_name='destinations')
    op.drop_index('ix_alarms_enabled_wake_time', table_name='alarms')
    op.drop_index('ix_alarms_user_id_status', table_name='alarms')
    op.drop_index('ix_alarms_calculated_leave_time', table_name='alarms')
