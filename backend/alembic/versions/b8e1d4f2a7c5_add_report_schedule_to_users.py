"""add report schedule to users

Revision ID: b8e1d4f2a7c5
Revises: a4d8f2c6b9e3

Escolha de dia/hora (UTC) do resumo periódico por email - ver
app/scheduler.py::report_job (substitui o cron fixo sáb 08:00 UTC único para
todos). report_day_of_week segue datetime.weekday() (0=segunda..6=domingo).
Os valores por omissão (5, 8) preservam o comportamento anterior para
utilizadores já existentes. last_report_sent_at evita reenvio duplicado.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8e1d4f2a7c5'
down_revision = 'a4d8f2c6b9e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('report_day_of_week', sa.Integer(), nullable=False, server_default='5'),
    )
    op.add_column(
        'users',
        sa.Column('report_hour', sa.Integer(), nullable=False, server_default='8'),
    )
    op.add_column('users', sa.Column('last_report_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_report_sent_at')
    op.drop_column('users', 'report_hour')
    op.drop_column('users', 'report_day_of_week')
