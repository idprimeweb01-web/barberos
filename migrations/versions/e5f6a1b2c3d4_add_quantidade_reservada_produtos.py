"""add quantidade_reservada to produtos

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a1b2c3d4'
down_revision = 'd4e5f6a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('produtos', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'quantidade_reservada', sa.Integer(), nullable=False,
            server_default='0',
        ))


def downgrade():
    with op.batch_alter_table('produtos', schema=None) as batch_op:
        batch_op.drop_column('quantidade_reservada')
