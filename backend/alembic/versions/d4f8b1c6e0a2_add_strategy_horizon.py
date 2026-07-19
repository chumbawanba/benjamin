"""add horizon to strategy_templates

Revision ID: d4f8b1c6e0a2
Revises: c1d4e9a2f7b3

Permite classificar uma estratégia como curto/longo prazo — usado para
agrupar e etiquetar os sinais no Overview (secção "Sinais" separada por
estratégia, pedido do utilizador em 2026-07-18).
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f8b1c6e0a2'
down_revision = 'c1d4e9a2f7b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategy_templates', sa.Column('horizon', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('strategy_templates', 'horizon')
