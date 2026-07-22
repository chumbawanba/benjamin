"""add waitlist_entries table

Revision ID: c8d3a5f9b1e7
Revises: b2c3d4e5f6a7

Tabela para guardar emails de interessados recolhidos na landing page
(appbenjamin.com) - não são utilizadores da app, só um formulário público de
captação de contacto.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c8d3a5f9b1e7'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'waitlist_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('email', name='uq_waitlist_entries_email'),
    )


def downgrade() -> None:
    op.drop_table('waitlist_entries')
