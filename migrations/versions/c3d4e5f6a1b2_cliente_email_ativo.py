"""add email and ativo to clientes

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a1b2'
down_revision = 'b2c3d4e5f6a1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('ativo', sa.Boolean(), nullable=False,
                                      server_default=sa.text('true')))


def downgrade():
    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.drop_column('ativo')
        batch_op.drop_column('email')
