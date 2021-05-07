"""create_donors_overview_table

Revision ID: 217337f9b133
Revises: 149e19e8c994
Create Date: 2020-09-27 10:17:45.269089

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "217337f9b133"
down_revision = "9d51ae0ab1e0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "donors_overview",
        sa.Column("rodne_cislo", sa.String(length=10), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("postal_code", sa.String(length=5), nullable=False),
        sa.Column("kod_pojistovny", sa.String(length=3), nullable=False),
        sa.Column("donation_count_fm", sa.Integer(), nullable=False),
        sa.Column("donation_count_fm_bubenik", sa.Integer(), nullable=False),
        sa.Column("donation_count_trinec", sa.Integer(), nullable=False),
        sa.Column("donation_count_mp", sa.Integer(), nullable=False),
        sa.Column("donation_count_total", sa.Integer(), nullable=False),
        sa.Column("donation_count_manual", sa.Integer(), nullable=False),
        sa.Column("awarded_medal_br", sa.Boolean(), nullable=False),
        sa.Column("awarded_medal_st", sa.Boolean(), nullable=False),
        sa.Column("awarded_medal_zl", sa.Boolean(), nullable=False),
        sa.Column("awarded_medal_kr3", sa.Boolean(), nullable=False),
        sa.Column("awarded_medal_kr2", sa.Boolean(), nullable=False),
        sa.Column("awarded_medal_kr1", sa.Boolean(), nullable=False),
        sa.Column("awarded_medal_plk", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("rodne_cislo"),
    )


def downgrade():
    op.drop_table("donors_overview")
