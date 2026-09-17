"""add other_assets table

Revision ID: 53849ddfb8d8
Revises: 8e77a41ac464

Ativos fora do Portfolio de ações/ETFs/cash (imóveis, certificados de
aforro/tesouro, etc.) - espelho do Loan do lado do ativo.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '53849ddfb8d8'
down_revision = '8e77a41ac464'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'other_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('value', sa.Numeric(14, 2), nullable=False),
        sa.Column('expected_return_pct', sa.Numeric(6, 3), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category IN ('imovel', 'outro')", name='ck_other_assets_category'),
    )


def downgrade() -> None:
    op.drop_table('other_assets')
