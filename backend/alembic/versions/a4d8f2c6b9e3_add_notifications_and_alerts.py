"""add notifications and alerts

Revision ID: a4d8f2c6b9e3
Revises: 37f0a9ee6093

Suporte para alertas (preço/sinal, ver app/services/alerts.py) e notificações
in-app + email (ver app/services/notifications.py, app/routers/notifications.py):
- users: toggles de email (relatório periódico / alertas) + unsubscribe_token
  (link de cancelar subscrição sem login).
- watchlist_items: opt-in de alerta de sinal + estado "já disparado" dos
  alertas de preço (edge-triggered, para não repetir o alerta em toda corrida
  do job diário enquanto o preço se mantém cruzado).
- notifications: centro de notificações in-app, que serve também de registo
  do que já foi enviado.
"""
import secrets

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a4d8f2c6b9e3'
down_revision = '37f0a9ee6093'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('email_reports_enabled', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.add_column(
        'users',
        sa.Column('email_alerts_enabled', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.add_column('users', sa.Column('unsubscribe_token', sa.String(length=64), nullable=True))

    # Backfill de unsubscribe_token para utilizadores já existentes - não dá
    # para ter um server_default fixo para uma coluna que tem de ser única.
    conn = op.get_bind()
    user_ids = [row[0] for row in conn.execute(sa.text('SELECT id FROM users')).fetchall()]
    for user_id in user_ids:
        conn.execute(
            sa.text('UPDATE users SET unsubscribe_token = :token WHERE id = :id'),
            {'token': secrets.token_urlsafe(32), 'id': user_id},
        )
    op.alter_column('users', 'unsubscribe_token', nullable=False)
    op.create_unique_constraint('uq_users_unsubscribe_token', 'users', ['unsubscribe_token'])

    op.add_column(
        'watchlist_items',
        sa.Column('alert_on_signal', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'watchlist_items',
        sa.Column('buy_alert_triggered', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'watchlist_items',
        sa.Column('sell_alert_triggered', sa.Boolean(), nullable=False, server_default='false'),
    )

    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stock_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stocks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_column('watchlist_items', 'sell_alert_triggered')
    op.drop_column('watchlist_items', 'buy_alert_triggered')
    op.drop_column('watchlist_items', 'alert_on_signal')
    op.drop_constraint('uq_users_unsubscribe_token', 'users', type_='unique')
    op.drop_column('users', 'unsubscribe_token')
    op.drop_column('users', 'email_alerts_enabled')
    op.drop_column('users', 'email_reports_enabled')
