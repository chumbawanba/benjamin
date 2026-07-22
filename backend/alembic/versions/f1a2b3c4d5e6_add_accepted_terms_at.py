"""add accepted_terms_at to users and waitlist_entries

Revision ID: f1a2b3c4d5e6
Revises: e2f7a4b9c1d3

Aceitação obrigatória da Política de Privacidade e de Cookies no registo de
conta e na inscrição na newsletter (ver RegisterIn/WaitlistIn em
schemas/common.py e routers/auth.py, routers/waitlist.py). Nullable porque
registos/inscrições anteriores a esta funcionalidade não têm este campo.
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e2f7a4b9c1d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('accepted_terms_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('waitlist_entries', sa.Column('accepted_terms_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('waitlist_entries', 'accepted_terms_at')
    op.drop_column('users', 'accepted_terms_at')
