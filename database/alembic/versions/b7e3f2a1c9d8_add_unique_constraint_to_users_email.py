"""add_unique_constraint_to_users_email

Revision ID: b7e3f2a1c9d8
Revises: a3b2c1d4e5f6
Create Date: 2026-02-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e3f2a1c9d8'
down_revision: Union[str, Sequence[str], None] = 'a3b2c1d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Clean up duplicate emails, then add unique constraint."""
    conn = op.get_bind()

    # Find duplicate emails
    duplicates = conn.execute(
        sa.text("""
            SELECT email, COUNT(*) as cnt
            FROM users
            GROUP BY email
            HAVING COUNT(*) > 1
        """)
    ).fetchall()

    for email, cnt in duplicates:
        # For each duplicate email group, keep the best one and delete the rest.
        # Priority: verified > unverified, then most recently created.
        rows = conn.execute(
            sa.text("""
                SELECT id, email_verified, created_at
                FROM users
                WHERE email = :email
                ORDER BY email_verified DESC, created_at DESC
            """),
            {"email": email},
        ).fetchall()

        # Keep the first (best) row, delete the rest one by one
        for row in rows[1:]:
            delete_id = str(row[0])
            conn.execute(
                sa.text("DELETE FROM profiles WHERE user_id = :uid"),
                {"uid": delete_id},
            )
            conn.execute(
                sa.text("DELETE FROM users WHERE id = :uid"),
                {"uid": delete_id},
            )

    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    """Remove unique constraint from users.email column."""
    op.drop_constraint('uq_users_email', 'users', type_='unique')
