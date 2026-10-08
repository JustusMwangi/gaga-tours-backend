"""tour category & destination many-to-many

Converts the single-select tour.category_id / tour.destination_id foreign keys
into many-to-many link tables so a tour can span several categories
(bush, family & kids, group…) and several destinations.

Revision ID: c3a7d1e9b2f4
Revises: aa656c1fcee2
Create Date: 2026-05-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a7d1e9b2f4'
down_revision = 'aa656c1fcee2'
branch_labels = None
depends_on = None


def upgrade():
    # 1. New link tables
    op.create_table(
        'tour_category_links',
        sa.Column('tour_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['tour_id'], ['tours.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['tour_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tour_id', 'category_id'),
    )
    op.create_table(
        'tour_destination_links',
        sa.Column('tour_id', sa.Uuid(), nullable=False),
        sa.Column('destination_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['tour_id'], ['tours.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['destination_id'], ['destinations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tour_id', 'destination_id'),
    )

    # 2. Backfill from the existing single foreign keys
    op.execute(
        "INSERT INTO tour_category_links (tour_id, category_id) "
        "SELECT id, category_id FROM tours WHERE category_id IS NOT NULL"
    )
    op.execute(
        "INSERT INTO tour_destination_links (tour_id, destination_id) "
        "SELECT id, destination_id FROM tours WHERE destination_id IS NOT NULL"
    )

    # 3. Drop the now-redundant single FK columns (Postgres drops their
    #    FK constraints with them).
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.drop_column('category_id')
        batch_op.drop_column('destination_id')


def downgrade():
    # 1. Re-add the single FK columns
    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('destination_id', sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            'tours_category_id_fkey', 'tour_categories',
            ['category_id'], ['id'], ondelete='SET NULL',
        )
        batch_op.create_foreign_key(
            'tours_destination_id_fkey', 'destinations',
            ['destination_id'], ['id'], ondelete='SET NULL',
        )

    # 2. Backfill a single value (arbitrary first link) back onto the tour
    op.execute(
        "UPDATE tours SET category_id = ("
        "SELECT category_id FROM tour_category_links "
        "WHERE tour_category_links.tour_id = tours.id LIMIT 1)"
    )
    op.execute(
        "UPDATE tours SET destination_id = ("
        "SELECT destination_id FROM tour_destination_links "
        "WHERE tour_destination_links.tour_id = tours.id LIMIT 1)"
    )

    # 3. Drop the link tables
    op.drop_table('tour_destination_links')
    op.drop_table('tour_category_links')
