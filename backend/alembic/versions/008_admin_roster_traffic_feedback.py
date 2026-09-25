"""Admin page: users.is_admin, page_views, feedback

Revision ID: 008
Revises: 007
Create Date: 2026-09-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        'page_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_page_views_id'), 'page_views', ['id'], unique=False)
    op.create_index(op.f('ix_page_views_user_id'), 'page_views', ['user_id'], unique=False)
    op.create_index(op.f('ix_page_views_path'), 'page_views', ['path'], unique=False)
    op.create_index(op.f('ix_page_views_created_at'), 'page_views', ['created_at'], unique=False)

    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)
    op.create_index(op.f('ix_feedback_user_id'), 'feedback', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_user_id'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback')

    op.drop_index(op.f('ix_page_views_created_at'), table_name='page_views')
    op.drop_index(op.f('ix_page_views_path'), table_name='page_views')
    op.drop_index(op.f('ix_page_views_user_id'), table_name='page_views')
    op.drop_index(op.f('ix_page_views_id'), table_name='page_views')
    op.drop_table('page_views')

    op.drop_column('users', 'is_admin')
