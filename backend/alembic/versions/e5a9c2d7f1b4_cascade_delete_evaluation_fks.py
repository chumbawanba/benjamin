"""cascade delete on evaluation FKs referencing strategies/items

Revision ID: e5a9c2d7f1b4
Revises: d4f8b1c6e0a2

Bug encontrado ao vivo: apagar um StrategyItem (ou um StrategyTemplate
inteiro) que já tinha sido avaliado pelo menos uma vez falhava com
IntegrityError (violação de FK em evaluation_details/evaluations), porque
nenhuma das duas FKs tinha ON DELETE CASCADE. No ambiente do utilizador isto
não aparecia como um erro HTTP normal — a exceção não tratada fazia a ligação
cair, e o browser via isso como "Failed to fetch"/erro de rede, não como um
500 explicável (mesmo padrão do bug do 503 causado pela coluna `horizon` em
falta). Como agora as estratégias são avaliadas automaticamente ao adicionar
uma ação à watchlist, isto deixou de ser um caso raro.

Os nomes das constraints (`evaluation_details_checklist_item_id_fkey` e
`evaluations_strategy_template_id_fkey`) refletem o nome ORIGINAL das
colunas antes do rename Checklist->Strategy (migração 8f2a1c9d4b6e) —
`ALTER COLUMN ... RENAME` não renomeia a constraint associada.
"""
from alembic import op

revision = 'e5a9c2d7f1b4'
down_revision = 'd4f8b1c6e0a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        'evaluation_details_checklist_item_id_fkey', 'evaluation_details', type_='foreignkey',
    )
    op.create_foreign_key(
        'evaluation_details_strategy_item_id_fkey', 'evaluation_details', 'strategy_items',
        ['strategy_item_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_constraint(
        'evaluations_checklist_template_id_fkey', 'evaluations', type_='foreignkey',
    )
    op.create_foreign_key(
        'evaluations_strategy_template_id_fkey', 'evaluations', 'strategy_templates',
        ['strategy_template_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'evaluations_strategy_template_id_fkey', 'evaluations', type_='foreignkey',
    )
    op.create_foreign_key(
        'evaluations_checklist_template_id_fkey', 'evaluations', 'strategy_templates',
        ['strategy_template_id'], ['id'],
    )
    op.drop_constraint(
        'evaluation_details_strategy_item_id_fkey', 'evaluation_details', type_='foreignkey',
    )
    op.create_foreign_key(
        'evaluation_details_checklist_item_id_fkey', 'evaluation_details', 'strategy_items',
        ['strategy_item_id'], ['id'],
    )
