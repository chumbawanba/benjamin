"""add last_quote_at to stocks

Revision ID: c9d3a5f7b1e4
Revises: b7e4d1f9a6c2

Regista quando a cotação intradiária (Finnhub /quote) foi obtida pela última
vez - permite ao ensure_fresh atualizá-la a cada QUOTE_REFRESH_COOLDOWN em vez
de só uma vez por dia, e ao frontend mostrar "atualizado há X min" (ver
app/services/market_data.py). Sem isto o preço mostrado ficava congelado no
valor da primeira consulta do dia e não refletia movimentos intradiários.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d3a5f7b1e4'
down_revision = 'b7e4d1f9a6c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stocks', sa.Column('last_quote_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('stocks', 'last_quote_at')
