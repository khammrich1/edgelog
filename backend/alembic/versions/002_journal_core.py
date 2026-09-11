"""Journal core: trading days and morning checklist (VS2)

Revision ID: 002
Revises: 001
Create Date: 2026-09-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trading_days',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('sleep_quality', sa.Integer(), nullable=True),
        sa.Column('mood', sa.Integer(), nullable=True),
        sa.Column('market_bias', sa.Text(), nullable=True),
        sa.Column('bias_chart_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_trading_day_user_date'),
    )
    op.create_index(op.f('ix_trading_days_id'), 'trading_days', ['id'], unique=False)
    op.create_index(op.f('ix_trading_days_user_id'), 'trading_days', ['user_id'], unique=False)
    op.create_index(op.f('ix_trading_days_date'), 'trading_days', ['date'], unique=False)

    op.create_table(
        'checklist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_checklist_items_id'), 'checklist_items', ['id'], unique=False)
    op.create_index(op.f('ix_checklist_items_user_id'), 'checklist_items', ['user_id'], unique=False)

    op.create_table(
        'trading_day_checklist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trading_day_id', sa.Integer(), nullable=False),
        sa.Column('checklist_item_id', sa.Integer(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['trading_day_id'], ['trading_days.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['checklist_item_id'], ['checklist_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trading_day_id', 'checklist_item_id', name='uq_day_checklist_item'),
    )
    op.create_index(
        op.f('ix_trading_day_checklist_items_id'), 'trading_day_checklist_items', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_trading_day_checklist_items_trading_day_id'),
        'trading_day_checklist_items', ['trading_day_id'], unique=False
    )
    op.create_index(
        op.f('ix_trading_day_checklist_items_checklist_item_id'),
        'trading_day_checklist_items', ['checklist_item_id'], unique=False
    )


def downgrade() -> None:
    op.drop_table('trading_day_checklist_items')
    op.drop_index(op.f('ix_checklist_items_user_id'), table_name='checklist_items')
    op.drop_index(op.f('ix_checklist_items_id'), table_name='checklist_items')
    op.drop_table('checklist_items')
    op.drop_index(op.f('ix_trading_days_date'), table_name='trading_days')
    op.drop_index(op.f('ix_trading_days_user_id'), table_name='trading_days')
    op.drop_index(op.f('ix_trading_days_id'), table_name='trading_days')
    op.drop_table('trading_days')
