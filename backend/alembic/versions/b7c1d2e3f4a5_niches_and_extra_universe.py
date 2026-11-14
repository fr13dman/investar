"""niches and extra (non-index) universe

Revision ID: b7c1d2e3f4a5
Revises: 55980ed370b4
Create Date: 2026-11-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = '55980ed370b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('asset_type', sa.String(length=10), nullable=False, server_default='stock'))
    op.add_column('companies', sa.Column('extra_source', sa.String(length=10), nullable=True))
    op.create_index(op.f('ix_companies_extra_source'), 'companies', ['extra_source'], unique=False)
    op.create_table('niches',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['niches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_niches_parent_id'), 'niches', ['parent_id'], unique=False)
    op.create_table('niche_members',
    sa.Column('niche_id', sa.Integer(), nullable=False),
    sa.Column('ticker', sa.String(length=12), nullable=False),
    sa.Column('source', sa.String(length=10), nullable=False),
    sa.ForeignKeyConstraint(['niche_id'], ['niches.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['ticker'], ['companies.ticker'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('niche_id', 'ticker')
    )
    op.create_index(op.f('ix_niche_members_ticker'), 'niche_members', ['ticker'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_niche_members_ticker'), table_name='niche_members')
    op.drop_table('niche_members')
    op.drop_index(op.f('ix_niches_parent_id'), table_name='niches')
    op.drop_table('niches')
    op.drop_index(op.f('ix_companies_extra_source'), table_name='companies')
    with op.batch_alter_table('companies') as batch:
        batch.drop_column('extra_source')
        batch.drop_column('asset_type')
