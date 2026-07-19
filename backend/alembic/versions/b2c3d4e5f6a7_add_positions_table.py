"""add positions table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6

Posições reais (quantidade + preço médio de custo) para a nova página
Portfolio — independente da watchlist, uma posição por ação por utilizador.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stock_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stocks.id'), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
        sa.Column('avg_cost', sa.Numeric(12, 4), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'stock_id', name='uq_positions_user_stock'),
    )


def downgrade() -> None:
    op.drop_table('positions')
