"""unique barbeiro in configuracao_agenda

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Remove duplicatas mantendo apenas a config mais recente por barbeiro
    op.execute("""
        DELETE FROM configuracao_agenda
        WHERE id NOT IN (
            SELECT DISTINCT ON (barbeiro_id) id
            FROM configuracao_agenda
            ORDER BY barbeiro_id, id DESC
        )
    """)
    with op.batch_alter_table('configuracao_agenda', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_configuracao_agenda_barbeiro', ['barbeiro_id'])


def downgrade():
    with op.batch_alter_table('configuracao_agenda', schema=None) as batch_op:
        batch_op.drop_constraint('uq_configuracao_agenda_barbeiro', type_='unique')
