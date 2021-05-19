"""create_medals_tables

Revision ID: 9d51ae0ab1e0
Revises: 149e19e8c994
Create Date: 2020-09-25 17:30:04.933587

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9d51ae0ab1e0"
down_revision = "149e19e8c994"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "medals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "awarded_medals",
        sa.Column("rodne_cislo", sa.String(length=10), nullable=False),
        sa.Column("medal_id", sa.Integer(), nullable=False),
        sa.Column("awarded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["medal_id"],
            ["medals.id"],
        ),
        sa.PrimaryKeyConstraint("rodne_cislo", "medal_id"),
    )
    op.create_index(
        op.f("ix_awarded_medals_rodne_cislo"),
        "awarded_medals",
        ["rodne_cislo"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_awarded_medals_rodne_cislo"), table_name="awarded_medals")
    op.drop_table("awarded_medals")
    op.drop_table("medals")
