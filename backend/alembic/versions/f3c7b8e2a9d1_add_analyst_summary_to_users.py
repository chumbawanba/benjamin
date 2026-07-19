"""add analyst summary columns to users

Revision ID: f3c7b8e2a9d1
Revises: e5a9c2d7f1b4

Resumo do analista (Overview): singleton por utilizador, gerado via LLM
(OpenAI) a partir da watchlist + contexto geral de mercado. Guardado
diretamente no User em vez de numa tabela dedicada porque é um valor único
por utilizador, sem necessidade de histórico no MVP - atualizado manualmente
pelo utilizador (nunca em background), não corre no scheduler.
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3c7b8e2a9d1'
down_revision = 'e5a9c2d7f1b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('analyst_summary', sa.Text(), nullable=True))
    op.add_column(
        'users', sa.Column('analyst_summary_generated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'analyst_summary_generated_at')
    op.drop_column('users', 'analyst_summary')
