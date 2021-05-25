"""create_donors_override

Revision ID: 60a681c463a2
Revises: 467ee396a68e
Create Date: 2021-05-25 12:50:58.779359

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "60a681c463a2"
down_revision = "467ee396a68e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "donors_override",
        sa.Column("rodne_cislo", sa.CHAR(length=10), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("postal_code", sa.CHAR(length=5), nullable=True),
        sa.Column("kod_pojistovny", sa.CHAR(length=3), nullable=True),
        sa.PrimaryKeyConstraint("rodne_cislo"),
    )


def downgrade():
    op.drop_table("donors_override")
