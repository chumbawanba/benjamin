"""add fx_rate_snapshots table and users.preferred_currency

Revision ID: d1e6f2a8c4b9
Revises: c8d3a5f9b1e7

Suporte a portfolio em várias moedas: cache de taxas de câmbio +
moeda preferida por utilizador para apresentar os totais convertidos.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd1e6f2a8c4b9'
down_revision = 'c8d3a5f9b1e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('preferred_currency', sa.String(3), nullable=False, server_default='EUR'),
    )
    op.create_table(
        'fx_rate_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('quote_currency', sa.String(3), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('rate', sa.Numeric(18, 8), nullable=False),
        sa.UniqueConstraint('base_currency', 'quote_currency', 'date', name='uq_fx_rate_snapshots_pair_date'),
    )


def downgrade() -> None:
    op.drop_table('fx_rate_snapshots')
    op.drop_column('users', 'preferred_currency')
