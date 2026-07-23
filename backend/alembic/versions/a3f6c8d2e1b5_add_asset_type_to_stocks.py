"""add asset_type to stocks

Revision ID: a3f6c8d2e1b5
Revises: f1a2b3c4d5e6

Distingue acções de ETFs (ver app/services/market_data.py) - refresh_fundamentals
deixa de chamar o endpoint de fundamentais de empresa (/stock/metric) para ETFs,
que devolve sempre vazio para esse tipo de instrumento. Default "stock" para
todos os tickers já existentes.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a3f6c8d2e1b5'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'stocks',
        sa.Column('asset_type', sa.String(10), nullable=False, server_default='stock'),
    )


def downgrade() -> None:
    op.drop_column('stocks', 'asset_type')
