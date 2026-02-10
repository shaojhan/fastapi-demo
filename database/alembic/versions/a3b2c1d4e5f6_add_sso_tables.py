"""add sso_providers, sso_config, sso_user_links tables

Revision ID: a3b2c1d4e5f6
Revises: 01ce1a251126
Create Date: 2026-02-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b2c1d4e5f6'
down_revision: Union[str, Sequence[str], None] = '01ce1a251126'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # sso_providers
    op.create_table('sso_providers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('protocol', sa.Enum('SAML', 'OIDC', name='ssoprotocol'), nullable=False),
        # SAML fields
        sa.Column('idp_entity_id', sa.String(length=512), nullable=True),
        sa.Column('idp_sso_url', sa.String(length=512), nullable=True),
        sa.Column('idp_slo_url', sa.String(length=512), nullable=True),
        sa.Column('idp_x509_cert', sa.Text(), nullable=True),
        sa.Column('sp_entity_id', sa.String(length=512), nullable=True),
        sa.Column('sp_acs_url', sa.String(length=512), nullable=True),
        # OIDC fields
        sa.Column('client_id', sa.String(length=255), nullable=True),
        sa.Column('client_secret', sa.Text(), nullable=True),
        sa.Column('authorization_url', sa.String(length=512), nullable=True),
        sa.Column('token_url', sa.String(length=512), nullable=True),
        sa.Column('userinfo_url', sa.String(length=512), nullable=True),
        sa.Column('jwks_uri', sa.String(length=512), nullable=True),
        sa.Column('scopes', sa.String(length=512), nullable=True),
        # Common
        sa.Column('attribute_mapping', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_sso_providers_slug', 'sso_providers', ['slug'], unique=False)
    op.create_index('ix_sso_providers_is_active', 'sso_providers', ['is_active'], unique=False)

    # sso_config (singleton)
    op.create_table('sso_config',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('auto_create_users', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('enforce_sso', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('default_role', sa.String(length=32), server_default='NORMAL', nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # sso_user_links
    op.create_table('sso_user_links',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('provider_id', sa.Uuid(), nullable=False),
        sa.Column('external_id', sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_id'], ['sso_providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_id', 'external_id', name='uq_provider_external_id'),
    )
    op.create_index('ix_sso_user_links_user_id', 'sso_user_links', ['user_id'], unique=False)
    op.create_index('ix_sso_user_links_provider_id', 'sso_user_links', ['provider_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sso_user_links_provider_id', table_name='sso_user_links')
    op.drop_index('ix_sso_user_links_user_id', table_name='sso_user_links')
    op.drop_table('sso_user_links')
    op.drop_table('sso_config')
    op.drop_index('ix_sso_providers_is_active', table_name='sso_providers')
    op.drop_index('ix_sso_providers_slug', table_name='sso_providers')
    op.drop_table('sso_providers')
