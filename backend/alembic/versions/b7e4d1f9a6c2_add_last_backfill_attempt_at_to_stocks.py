"""add last_backfill_attempt_at to stocks

Revision ID: b7e4d1f9a6c2
Revises: a3f6c8d2e1b5

Separa "última tentativa de backfill" de "última snapshot com sucesso" (ver
app/services/market_data.py, ensure_fresh) - sem isto, um ticker cuja Finnhub/
Twelve Data rejeita (ex: cotado fora dos EUA, fora de cobertura do plano
gratuito) tentava sempre o backfill completo em toda a visita à página,
esgotando a quota partilhada da Twelve Data (800 pedidos/dia) para as
restantes ações da watchlist.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e4d1f9a6c2'
down_revision = 'a3f6c8d2e1b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stocks', sa.Column('last_backfill_attempt_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('stocks', 'last_backfill_attempt_at')
