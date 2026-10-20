"""Issue #95: broker-account ownership registry. Additive, new table only
-- no change to any existing table, no backfill. Trade.account_id (added
in migration 011, still unwritten by any route) is left exactly as-is;
this migration does not read it, infer anything from it, or create
BrokerAccount rows from it. Every row this slice's routes create is
unverified by construction (see app/models/broker_accounts.py) -- there
is no provider-backed verification mechanism yet for this migration to
encode, only the registry and the uniqueness rules a real one will need.

Revision ID: 012
Revises: 011
Create Date: 2026-10-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'broker_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('verification_status', sa.String(), nullable=False, server_default='unverified'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_broker_accounts_user_id', 'broker_accounts', ['user_id'])

    # A trader can't register the same (provider, account_id) twice.
    op.create_index(
        'uq_broker_account_user_provider_account',
        'broker_accounts',
        ['user_id', 'provider', 'account_id'],
        unique=True,
    )
    # At most one user may ever hold a VERIFIED claim on a given
    # (provider, account_id) -- a real account belongs to one person.
    # Unverified claims are intentionally unconstrained across users:
    # with no provider-backed check, there is nothing to arbitrate a
    # collision with, so refusing a second unverified claim would just
    # be a different unearned certainty, not a safer one.
    op.create_index(
        'uq_broker_account_verified_provider_account',
        'broker_accounts',
        ['provider', 'account_id'],
        unique=True,
        postgresql_where=sa.text("verification_status = 'verified'"),
    )


def downgrade() -> None:
    op.drop_index('uq_broker_account_verified_provider_account', table_name='broker_accounts')
    op.drop_index('uq_broker_account_user_provider_account', table_name='broker_accounts')
    op.drop_index('ix_broker_accounts_user_id', table_name='broker_accounts')
    op.drop_table('broker_accounts')
