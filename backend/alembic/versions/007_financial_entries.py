"""Annual P&L / Financial Tracker: financial_entries table

Revision ID: 007
Revises: 006
Create Date: 2026-09-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'financial_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('entry_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('firm', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_financial_entries_id'), 'financial_entries', ['id'], unique=False)
    op.create_index(op.f('ix_financial_entries_user_id'), 'financial_entries', ['user_id'], unique=False)
    op.create_index(op.f('ix_financial_entries_date'), 'financial_entries', ['date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_financial_entries_date'), table_name='financial_entries')
    op.drop_index(op.f('ix_financial_entries_user_id'), table_name='financial_entries')
    op.drop_index(op.f('ix_financial_entries_id'), table_name='financial_entries')
    op.drop_table('financial_entries')
