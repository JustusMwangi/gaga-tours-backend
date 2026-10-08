"""add_tour_youtube_url

Revision ID: aa656c1fcee2
Revises: 78c6e44fb9b9
Create Date: 2026-04-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa656c1fcee2'
down_revision = '78c6e44fb9b9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.add_column(sa.Column('youtube_url', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.drop_column('youtube_url')
