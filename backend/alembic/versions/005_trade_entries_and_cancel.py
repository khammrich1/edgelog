"""Trade scale-ins and cancellation (VS3): trade_entries table, trades.canceled_at

Revision ID: 005
Revises: 004
Create Date: 2026-09-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_TYPE = sa.Numeric(18, 6)


def upgrade() -> None:
    op.add_column('trades', sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'trade_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_price', PRICE_TYPE, nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trade_entries_id'), 'trade_entries', ['id'], unique=False)
    op.create_index(op.f('ix_trade_entries_trade_id'), 'trade_entries', ['trade_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_entries_trade_id'), table_name='trade_entries')
    op.drop_index(op.f('ix_trade_entries_id'), table_name='trade_entries')
    op.drop_table('trade_entries')
    op.drop_column('trades', 'canceled_at')
