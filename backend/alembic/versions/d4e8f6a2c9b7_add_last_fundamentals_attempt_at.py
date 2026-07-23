"""add last_fundamentals_attempt_at to stocks

Revision ID: d4e8f6a2c9b7
Revises: c9d3a5f7b1e4

Bug real: refresh_fundamentals só corria dentro do ramo de backfill do
ensure_fresh, nunca percorrido de novo por uma ação madura com histórico já
suficiente - os fundamentais (P/E, ROE, margens...) ficavam congelados no
valor da primeira vez que a ação foi adicionada à watchlist, para sempre.
Este campo permite chamar refresh_fundamentals sempre (útil para refletir
resultados trimestrais atualizados), com proteção contra tentativas repetidas
quando a Finnhub rejeita o símbolo (mesmo padrão de last_backfill_attempt_at/
last_quote_at - ver app/services/market_data.py).
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e8f6a2c9b7'
down_revision = 'c9d3a5f7b1e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stocks', sa.Column('last_fundamentals_attempt_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('stocks', 'last_fundamentals_attempt_at')
