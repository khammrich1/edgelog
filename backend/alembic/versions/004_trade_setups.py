"""Configurable trade setups (VS3): user-defined setup dropdown options

Revision ID: 004
Revises: 003
Create Date: 2026-09-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trade_setups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trade_setups_id'), 'trade_setups', ['id'], unique=False)
    op.create_index(op.f('ix_trade_setups_user_id'), 'trade_setups', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_setups_user_id'), table_name='trade_setups')
    op.drop_index(op.f('ix_trade_setups_id'), table_name='trade_setups')
    op.drop_table('trade_setups')
