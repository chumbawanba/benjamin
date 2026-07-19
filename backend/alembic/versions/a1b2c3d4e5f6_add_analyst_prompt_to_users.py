"""add analyst_prompt to users

Revision ID: a1b2c3d4e5f6
Revises: f3c7b8e2a9d1

Permite ao utilizador personalizar o prompt de sistema usado para gerar o
resumo do analista (Overview) antes de pedir uma análise — None mantém o
comportamento por omissão (DEFAULT_SYSTEM_PROMPT em analyst.py).
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f3c7b8e2a9d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('analyst_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'analyst_prompt')
