"""Trade extraction provenance (issue #64): track whether a trade's prices
came from manual entry or AI screenshot extraction, preserve the original
extracted values immutably, and flag when they're later edited.

Revision ID: 009
Revises: 008
Create Date: 2026-10-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trades',
        sa.Column('price_source', sa.String(), nullable=False, server_default='manual'),
    )
    op.add_column('trades', sa.Column('extraction_snapshot', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'trades',
        sa.Column('price_edited_after_extraction', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('trades', 'price_edited_after_extraction')
    op.drop_column('trades', 'extracted_at')
    op.drop_column('trades', 'extraction_snapshot')
    op.drop_column('trades', 'price_source')
