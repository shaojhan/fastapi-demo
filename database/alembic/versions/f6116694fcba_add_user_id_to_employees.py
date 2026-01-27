"""add_user_id_to_employees

Revision ID: f6116694fcba
Revises: 6a776c8f930f
Create Date: 2026-01-27 12:57:02.193108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6116694fcba'
down_revision: Union[str, Sequence[str], None] = '6a776c8f930f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('employees', sa.Column('user_id', sa.Uuid(), nullable=True))
    op.create_unique_constraint('uq_employees_user_id', 'employees', ['user_id'])
    op.create_foreign_key('fk_employees_user_id_users', 'employees', 'users', ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_employees_user_id_users', 'employees', type_='foreignkey')
    op.drop_constraint('uq_employees_user_id', 'employees', type_='unique')
    op.drop_column('employees', 'user_id')
