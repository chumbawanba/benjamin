"""add loans table

Revision ID: 8e77a41ac464
Revises: b8e1d4f2a7c5

Passivos do utilizador (empréstimos) — complementa o Portfolio (ativos) com
o lado da dívida, mesmo padrão simples de Position (só saldo atual, sem
histórico de pagamentos).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '8e77a41ac464'
down_revision = 'b8e1d4f2a7c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'loans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('balance', sa.Numeric(14, 2), nullable=False),
        sa.Column('interest_rate', sa.Numeric(6, 3), nullable=True),
        sa.Column('monthly_payment', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('loans')
