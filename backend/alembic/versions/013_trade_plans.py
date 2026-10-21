"""Issue #59: pre-trade plan table (Plan -> Review -> Approve/Reject).

Additive-only migration. TradePlan is a new, independent table -- it does
not touch trades/trade_entries/trade_exits/trading_days in any way, so no
existing data or behavior is affected. broker_account_id optionally
reuses the broker_accounts registry (issue #95, migration 012) instead of
a free-text account field.

Revision ID: 013
Revises: 012
Create Date: 2026-10-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_TYPE = sa.Numeric(18, 6)
AMOUNT_TYPE = sa.Numeric(14, 2)


def upgrade() -> None:
    op.create_table(
        'trade_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('previous_version_id', sa.Integer(), nullable=True),
        sa.Column('revision_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('broker_account_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('entry_price', PRICE_TYPE, nullable=False),
        sa.Column('stop_price', PRICE_TYPE, nullable=False),
        sa.Column('target_price', PRICE_TYPE, nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('max_risk_dollars', AMOUNT_TYPE, nullable=True),
        sa.Column('setup', sa.String(), nullable=True),
        sa.Column('invalidation_condition', sa.Text(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['previous_version_id'], ['trade_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['broker_account_id'], ['broker_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trade_plans_id'), 'trade_plans', ['id'], unique=False)
    op.create_index(op.f('ix_trade_plans_user_id'), 'trade_plans', ['user_id'], unique=False)
    op.create_index(op.f('ix_trade_plans_status'), 'trade_plans', ['status'], unique=False)
    op.create_index(op.f('ix_trade_plans_previous_version_id'), 'trade_plans', ['previous_version_id'], unique=False)
    op.create_index(op.f('ix_trade_plans_broker_account_id'), 'trade_plans', ['broker_account_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_plans_broker_account_id'), table_name='trade_plans')
    op.drop_index(op.f('ix_trade_plans_previous_version_id'), table_name='trade_plans')
    op.drop_index(op.f('ix_trade_plans_status'), table_name='trade_plans')
    op.drop_index(op.f('ix_trade_plans_user_id'), table_name='trade_plans')
    op.drop_index(op.f('ix_trade_plans_id'), table_name='trade_plans')
    op.drop_table('trade_plans')
