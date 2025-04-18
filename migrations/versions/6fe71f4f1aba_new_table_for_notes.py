"""New table for notes

Revision ID: 6fe71f4f1aba
Revises: 9c829c41652e
Create Date: 2021-03-21 11:33:27.533851

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6fe71f4f1aba"
down_revision = "9c829c41652e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "notes",
        sa.Column("rodne_cislo", sa.String(length=10), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("rodne_cislo"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("notes")
    # ### end Alembic commands ###
