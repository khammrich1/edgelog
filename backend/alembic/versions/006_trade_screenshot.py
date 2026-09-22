"""Trade screenshot storage (VS3/VS9): trades.screenshot_path

Revision ID: 006
Revises: 005
Create Date: 2026-09-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trades', sa.Column('screenshot_path', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('trades', 'screenshot_path')
