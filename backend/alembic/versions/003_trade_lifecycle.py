"""Trade lifecycle: trades and trade exits (VS3)

Revision ID: 003
Revises: 002
Create Date: 2026-09-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_TYPE = sa.Numeric(18, 6)


def upgrade() -> None:
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('trading_day_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('entry_price', PRICE_TYPE, nullable=False),
        sa.Column('initial_quantity', sa.Integer(), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stop_price', PRICE_TYPE, nullable=True),
        sa.Column('target_price', PRICE_TYPE, nullable=True),
        sa.Column('setup', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trading_day_id'], ['trading_days.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    op.create_index(op.f('ix_trades_user_id'), 'trades', ['user_id'], unique=False)
    op.create_index(op.f('ix_trades_trading_day_id'), 'trades', ['trading_day_id'], unique=False)

    op.create_table(
        'trade_exits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('exit_price', PRICE_TYPE, nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trade_exits_id'), 'trade_exits', ['id'], unique=False)
    op.create_index(op.f('ix_trade_exits_trade_id'), 'trade_exits', ['trade_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_exits_trade_id'), table_name='trade_exits')
    op.drop_index(op.f('ix_trade_exits_id'), table_name='trade_exits')
    op.drop_table('trade_exits')
    op.drop_index(op.f('ix_trades_trading_day_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_user_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')
