"""add nome_exibicao to barbearias

Revision ID: a1b2c3d4e5f6
Revises: f4a8b2c3d9e1
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '36e50d6dc569'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('barbearias', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nome_exibicao', sa.String(length=150), nullable=True))


def downgrade():
    with op.batch_alter_table('barbearias', schema=None) as batch_op:
        batch_op.drop_column('nome_exibicao')
