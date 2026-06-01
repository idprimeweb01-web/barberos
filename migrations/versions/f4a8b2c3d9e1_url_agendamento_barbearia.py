"""url_agendamento barbearia

Revision ID: f4a8b2c3d9e1
Revises: 1d48f9d7cda0
Create Date: 2026-05-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f4a8b2c3d9e1'
down_revision = '1d48f9d7cda0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('barbearias', schema=None) as batch_op:
        batch_op.add_column(sa.Column('url_agendamento', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('barbearias', schema=None) as batch_op:
        batch_op.drop_column('url_agendamento')
