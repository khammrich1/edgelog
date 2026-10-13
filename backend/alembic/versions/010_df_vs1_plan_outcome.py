"""DF-VS1 (issue #78): plan-vs-outcome evidence capture on the existing
Trade/TradingDay rows. No parallel trade lifecycle -- every new column is
nullable and additive, scoped to the same canonical Trade/TradingDay a
trader already uses.

Revision ID: 010
Revises: 009
Create Date: 2026-10-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRICE_PRECISION = 18
PRICE_SCALE = 6


def upgrade() -> None:
    # Plan: the original intended stop/target/quantity/rationale, set once
    # at trade creation and never edited thereafter. plan_verified_at is
    # stamped by the server itself (never trader-supplied) only when the
    # trader affirms the plan was recorded before execution; null means the
    # trade was journaled retrospectively, so nothing here is ever labeled
    # verified pre-trade evidence unless the server's own clock says so.
    op.add_column('trades', sa.Column('planned_stop_price', sa.Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True))
    op.add_column('trades', sa.Column('planned_target_price', sa.Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True))
    op.add_column('trades', sa.Column('planned_quantity', sa.Integer(), nullable=True))
    op.add_column('trades', sa.Column('plan_rationale', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('plan_verified_at', sa.DateTime(timezone=True), nullable=True))

    # Outcome: judged after the fact, editable like any other post-trade field.
    op.add_column('trades', sa.Column('rule_adherence', sa.String(), nullable=True))  # yes | no | unknown
    op.add_column('trades', sa.Column('rule_adherence_note', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('reflection_notes', sa.Text(), nullable=True))

    # TradingDay: end-of-day reflection and an explicit no-trade-day marker.
    op.add_column('trading_days', sa.Column('intended_to_trade', sa.Boolean(), nullable=True))
    op.add_column('trading_days', sa.Column('eod_reflection', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('trading_days', 'eod_reflection')
    op.drop_column('trading_days', 'intended_to_trade')

    op.drop_column('trades', 'reflection_notes')
    op.drop_column('trades', 'rule_adherence_note')
    op.drop_column('trades', 'rule_adherence')
    op.drop_column('trades', 'plan_verified_at')
    op.drop_column('trades', 'plan_rationale')
    op.drop_column('trades', 'planned_quantity')
    op.drop_column('trades', 'planned_target_price')
    op.drop_column('trades', 'planned_stop_price')
