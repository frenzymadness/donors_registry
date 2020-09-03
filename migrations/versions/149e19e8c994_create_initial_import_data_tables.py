"""create_initial_import_data_tables

Revision ID: 149e19e8c994
Revises: 5ab07360b2ae
Create Date: 2020-09-03 11:14:17.035220

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '149e19e8c994'
down_revision = '5ab07360b2ae'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("donation_center",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug")
    )
    op.create_table("batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("donation_center", sa.Integer(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["donation_center"], ["donation_center.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch", sa.Integer(), nullable=False),
        sa.Column("rodne_cislo", sa.String(length=10), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("postal_code", sa.String(length=5), nullable=False),
        sa.Column("kod_pojistovny", sa.String(length=3), nullable=False),
        sa.Column("donation_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["batch"], ["batches.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_records_rodne_cislo"), "records", {"rodne_cislo"}, unique=False)


def downgrade():
    op.drop_table("records")
    op.drop_table("batches")
    op.drop_table("donation_center")
