"""add patrimony_snapshots table

Revision ID: fab9b653eb4e
Revises: 53849ddfb8d8

Histórico manual de património (fotografias pontuais do breakdown completo -
stocks/cash/outros ativos/dívida - numa data escolhida pelo utilizador), já
que Position/OtherAsset/Loan só guardam o valor atual, sem histórico.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'fab9b653eb4e'
down_revision = '53849ddfb8d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'patrimony_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('stocks_value', sa.Numeric(14, 2), nullable=False),
        sa.Column('cash_value', sa.Numeric(14, 2), nullable=False),
        sa.Column('other_assets_value', sa.Numeric(14, 2), nullable=False),
        sa.Column('loans_balance', sa.Numeric(14, 2), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'date', name='uq_patrimony_snapshots_user_date'),
    )


def downgrade() -> None:
    op.drop_table('patrimony_snapshots')
