"""fill_lists

Revision ID: 7eeb86607ef1
Revises: 9d51ae0ab1e0
Create Date: 2020-09-27 10:24:42.298975

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7eeb86607ef1"
down_revision = "9d51ae0ab1e0"
branch_labels = None
depends_on = None

donation_centers = sa.table(
    "donation_centers", sa.column("slug", sa.String), sa.column("title", sa.String)
)
medals = sa.table("medals", sa.column("slug", sa.String), sa.column("title", sa.String))


def upgrade():
    op.execute(
        donation_centers.insert().values(
            (
                {
                    donation_centers.c.slug: "fm",
                    donation_centers.c.title: "Frýdek-Místek",
                },
                {
                    donation_centers.c.slug: "fm_bubenik",
                    donation_centers.c.title: "Frýdek-Místek, Krevní centrum",
                },
                {donation_centers.c.slug: "trinec", donation_centers.c.title: "Třinec"},
            )
        )
    )
    op.execute(
        medals.insert().values(
            (
                {medals.c.slug: "br", medals.c.title: "Bronzová medaile"},
                {medals.c.slug: "st", medals.c.title: "Stříbrná medaile"},
                {medals.c.slug: "zl", medals.c.title: "Zlatá medaile"},
                {medals.c.slug: "kr3", medals.c.title: "Zlatý kříž 3. třídy"},
                {medals.c.slug: "kr2", medals.c.title: "Zlatý kříž 2. třídy"},
                {medals.c.slug: "kr1", medals.c.title: "Zlatý kříž 1. třídy"},
                {medals.c.slug: "plk", medals.c.title: "Plaketa ČČK"},
            )
        )
    )


def downgrade():
    op.execute(
        donation_centers.delete().where(
            donation_centers.c.slug.in_(("fm", "fm_bubenik", "trinec"))
        )
    )
    op.execute(
        medals.delete().where(
            medals.c.slug.in_(("br", "st", "zl", "kr3", "kr2", "kr1"))
        )
    )
