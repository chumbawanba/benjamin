"""add revenue_growth, net_margin, roe, current_ratio to fundamentals_snapshots

Revision ID: e2f7a4b9c1d3
Revises: d1e6f2a8c4b9

Mais métricas de "posição financeira" por ação (ver app/services/analyst.py) -
permite ao Benjamin responder melhor sobre lucros/saúde financeira de uma ação
específica, além dos 5 fundamentais já existentes (P/E, EPS, dívida/capital,
dividendo, cap. mercado).
"""
from alembic import op
import sqlalchemy as sa

revision = 'e2f7a4b9c1d3'
down_revision = 'd1e6f2a8c4b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('fundamentals_snapshots', sa.Column('revenue_growth', sa.Numeric(10, 2), nullable=True))
    op.add_column('fundamentals_snapshots', sa.Column('net_margin', sa.Numeric(10, 2), nullable=True))
    op.add_column('fundamentals_snapshots', sa.Column('roe', sa.Numeric(10, 2), nullable=True))
    op.add_column('fundamentals_snapshots', sa.Column('current_ratio', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('fundamentals_snapshots', 'current_ratio')
    op.drop_column('fundamentals_snapshots', 'roe')
    op.drop_column('fundamentals_snapshots', 'net_margin')
    op.drop_column('fundamentals_snapshots', 'revenue_growth')
