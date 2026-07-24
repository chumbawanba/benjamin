"""add peers cache to stocks

Revision ID: 37f0a9ee6093
Revises: e7f1b3c5d8a0

Cache dos "peers" (tickers de empresas parecidas, Finnhub /stock/peers) por
ação, usado na comparação de peers da StockDetail (ver
app/services/market_data.py::get_peers_cached). Cooldown de dias em vez de
minutos/horas - a composição de peers muda raramente, sem cache gastava-se
uma chamada Finnhub extra em toda visita à página.
"""
from alembic import op
import sqlalchemy as sa

revision = '37f0a9ee6093'
down_revision = 'e7f1b3c5d8a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stocks', sa.Column('peers_cache', sa.String(length=200), nullable=True))
    op.add_column('stocks', sa.Column('peers_fetched_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('stocks', 'peers_fetched_at')
    op.drop_column('stocks', 'peers_cache')
