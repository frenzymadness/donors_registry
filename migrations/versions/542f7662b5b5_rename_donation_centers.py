"""Rename donation centers

Revision ID: 542f7662b5b5
Revises: e1f6598ba415
Create Date: 2024-02-10 19:05:14.351967

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "542f7662b5b5"
down_revision = "e1f6598ba415"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE donation_centers SET title = 'Krevní centrum' WHERE slug = 'fm_bubenik';"
    )
    op.execute("UPDATE donation_centers SET title = 'Nemocnice F-M' WHERE slug = 'fm';")


def downgrade():
    op.execute(
        "UPDATE donation_centers SET title = 'Frýdek-Místek, Krevní centrum' WHERE slug = 'fm_bubenik';"
    )
    op.execute("UPDATE donation_centers SET title = 'Frýdek-Místek' WHERE slug = 'fm';")
