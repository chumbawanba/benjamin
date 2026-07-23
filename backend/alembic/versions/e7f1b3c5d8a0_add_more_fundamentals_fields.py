"""add gross_margin/operating_margin/eps_growth/dividend_growth_5y to fundamentals_snapshots

Revision ID: e7f1b3c5d8a0
Revises: d4e8f6a2c9b7

Desbloqueiam 3 estratégias de referência que faltavam na Biblioteca desde a
lista original de 26 (Dividend Growth, CAN SLIM, Piotroski F-Score
aproximado) - campos confirmados com payload real da Finnhub /stock/metric
(grossMarginTTM, operatingMarginTTM, epsGrowthTTMYoy, dividendGrowthRate5Y).
"""
from alembic import op
import sqlalchemy as sa

revision = 'e7f1b3c5d8a0'
down_revision = 'd4e8f6a2c9b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('fundamentals_snapshots', sa.Column('gross_margin', sa.Numeric(10, 2), nullable=True))
    op.add_column('fundamentals_snapshots', sa.Column('operating_margin', sa.Numeric(10, 2), nullable=True))
    op.add_column('fundamentals_snapshots', sa.Column('eps_growth', sa.Numeric(10, 2), nullable=True))
    op.add_column('fundamentals_snapshots', sa.Column('dividend_growth_5y', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('fundamentals_snapshots', 'dividend_growth_5y')
    op.drop_column('fundamentals_snapshots', 'eps_growth')
    op.drop_column('fundamentals_snapshots', 'operating_margin')
    op.drop_column('fundamentals_snapshots', 'gross_margin')
