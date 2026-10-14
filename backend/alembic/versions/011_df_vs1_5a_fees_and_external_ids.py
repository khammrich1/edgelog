"""DF-VS1.5a (issue #80): commission/fee capture for one-submission manual
completed-trade entry, plus external-ID/account columns needed by later
EOD-reconciliation slices so they don't require a second migration. All
columns nullable and additive -- no backfill, mirrors migration 010's
discipline. The external_*/account_* columns are unused by any UI or route
in this slice; they exist only so DF-VS1.5b/c can be built without
re-touching the schema.

Revision ID: 011
Revises: 010
Create Date: 2026-10-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AMOUNT_PRECISION = 14
AMOUNT_SCALE = 2


def upgrade() -> None:
    # Commission/fees per fill -- the original entry lives on Trade itself
    # (see trades.py's TradeEntry docstring), so Trade needs its own
    # commission/fees alongside TradeEntry/TradeExit's.
    op.add_column('trades', sa.Column('commission', sa.Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True))
    op.add_column('trades', sa.Column('fees', sa.Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True))
    op.add_column('trade_entries', sa.Column('commission', sa.Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True))
    op.add_column('trade_entries', sa.Column('fees', sa.Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True))
    op.add_column('trade_exits', sa.Column('commission', sa.Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True))
    op.add_column('trade_exits', sa.Column('fees', sa.Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True))

    # External/account identifiers (DF-VS1.5b/c groundwork, issue #80).
    op.add_column('trades', sa.Column('external_trade_id', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('external_order_id', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('account_id', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('account_label', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('trades', 'account_label')
    op.drop_column('trades', 'account_id')
    op.drop_column('trades', 'external_order_id')
    op.drop_column('trades', 'external_trade_id')

    op.drop_column('trade_exits', 'fees')
    op.drop_column('trade_exits', 'commission')
    op.drop_column('trade_entries', 'fees')
    op.drop_column('trade_entries', 'commission')
    op.drop_column('trades', 'fees')
    op.drop_column('trades', 'commission')
