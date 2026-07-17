"""rename checklist -> strategy

Revision ID: 8f2a1c9d4b6e
Revises: 133a97a36408

Rebranding: "Checklist" nunca foi um bom nome para isto — é uma estratégia de
scoring ponderado (metric+operator+threshold+weight), não uma lista simples de
tarefas. Esta migration renomeia tabelas/colunas em produção sem perder dados.
Aproveita também para corrigir o `weight` de strategy_items para NUMERIC(5,2)
(o modelo já tinha sido alargado para suportar o slider 0-100, mas nunca tinha
sido gerada a migration correspondente).
"""
from alembic import op
import sqlalchemy as sa


revision = '8f2a1c9d4b6e'
down_revision = '133a97a36408'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table('checklist_templates', 'strategy_templates')
    op.rename_table('checklist_items', 'strategy_items')
    op.alter_column(
        'strategy_items', 'weight',
        existing_type=sa.Numeric(precision=4, scale=2),
        type_=sa.Numeric(precision=5, scale=2),
        existing_nullable=False,
    )
    op.alter_column('evaluations', 'checklist_template_id', new_column_name='strategy_template_id')
    op.alter_column('evaluation_details', 'checklist_item_id', new_column_name='strategy_item_id')


def downgrade() -> None:
    op.alter_column('evaluation_details', 'strategy_item_id', new_column_name='checklist_item_id')
    op.alter_column('evaluations', 'strategy_template_id', new_column_name='checklist_template_id')
    op.alter_column(
        'strategy_items', 'weight',
        existing_type=sa.Numeric(precision=5, scale=2),
        type_=sa.Numeric(precision=4, scale=2),
        existing_nullable=False,
    )
    op.rename_table('strategy_items', 'checklist_items')
    op.rename_table('strategy_templates', 'checklist_templates')
