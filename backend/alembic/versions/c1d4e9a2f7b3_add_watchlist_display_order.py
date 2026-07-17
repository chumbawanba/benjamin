"""add display_order to watchlist_items

Revision ID: c1d4e9a2f7b3
Revises: 8f2a1c9d4b6e

Permite ao utilizador reordenar manualmente a watchlist (usado na página
Overview). Backfill preserva a ordem atual (mais recente primeiro) para quem
já tem dados, atribuindo display_order = 0, 1, 2... por utilizador.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c1d4e9a2f7b3'
down_revision = '8f2a1c9d4b6e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'watchlist_items',
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
    )
    op.execute(
        """
        UPDATE watchlist_items AS w
        SET display_order = ranked.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY added_at DESC) - 1 AS rn
            FROM watchlist_items
        ) AS ranked
        WHERE w.id = ranked.id
        """
    )


def downgrade() -> None:
    op.drop_column('watchlist_items', 'display_order')
