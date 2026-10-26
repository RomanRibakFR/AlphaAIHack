"""pd model 099: вход модели и параметры риска в решении

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-26 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # модель задачи 2 (models/pd): PD бывает и 0,05% — нужно больше знаков
    op.alter_column('decisions', 'pd', type_=sa.Numeric(precision=8, scale=6), existing_nullable=True)
    op.add_column('decisions', sa.Column('pd_at_requested_terms', sa.Numeric(precision=8, scale=6), nullable=True))
    op.add_column('decisions', sa.Column('lgd', sa.Numeric(precision=6, scale=4), nullable=True))
    op.add_column('decisions', sa.Column('product_pd_max', sa.Numeric(precision=6, scale=4), nullable=True))
    op.add_column('decisions', sa.Column('model_inputs', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('decisions', sa.Column('clipping_warnings', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('decisions', 'clipping_warnings')
    op.drop_column('decisions', 'model_inputs')
    op.drop_column('decisions', 'product_pd_max')
    op.drop_column('decisions', 'lgd')
    op.drop_column('decisions', 'pd_at_requested_terms')
    op.alter_column('decisions', 'pd', type_=sa.Numeric(precision=6, scale=4), existing_nullable=True)
