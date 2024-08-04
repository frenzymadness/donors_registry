"""new column for donation centers: import_increments

Revision ID: 56b8d32bbc2a
Revises: 542f7662b5b5
Create Date: 2024-08-04 11:06:29.403527

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "56b8d32bbc2a"
down_revision = "542f7662b5b5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "donation_centers", sa.Column("import_increments", sa.Boolean(), nullable=True)
    )

    op.execute("UPDATE donation_centers SET import_increments = 1 WHERE id = 4;")
    op.execute("UPDATE donation_centers SET import_increments = 0 WHERE id <> 4;")


def downgrade():
    op.drop_column("donation_centers", "import_increments")
