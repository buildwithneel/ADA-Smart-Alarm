"""add_firebase_uid_to_users

Revision ID: e16e1e3b2cb1
Revises: 30bfdd69790a
Create Date: 2026-09-30 14:28:40.640442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e16e1e3b2cb1'
down_revision: Union[str, None] = '30bfdd69790a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column with fallback default for any existing rows to prevent failure
    op.add_column(
        'users',
        sa.Column(
            'firebase_uid',
            sa.String(length=128),
            server_default=sa.text("'dev-user-firebase-uid-001'"),
            nullable=False,
        )
    )
    # Remove server_default so future inserts must explicitly provide firebase_uid
    op.alter_column('users', 'firebase_uid', server_default=None)
    op.create_index(op.f('ix_users_firebase_uid'), 'users', ['firebase_uid'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_firebase_uid'), table_name='users')
    op.drop_column('users', 'firebase_uid')
