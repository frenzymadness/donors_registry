"""New columns for medals

Revision ID: 467ee396a68e
Revises: 971ddb205e0c
Create Date: 2021-07-08 18:08:36.664990

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "467ee396a68e"
down_revision = "971ddb205e0c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("medals", sa.Column("title_acc", sa.String(), nullable=True))
    op.add_column("medals", sa.Column("title_instr", sa.String(), nullable=True))
    op.execute(
        "UPDATE medals SET title_acc = 'bronzovou medaili', title_instr = 'bronzovou medailí' WHERE slug = 'br';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'stříbrnou medaili', title_instr = 'stříbrnou medailí' WHERE slug = 'st';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatou medaili', title_instr = 'zlatou medailí' WHERE slug = 'zl';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatý kříž 3. třídy', title_instr = 'zlatým křížem 3. třídy' WHERE slug = 'kr3';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatý kříž 2. třídy', title_instr = 'zlatým křížem 2. třídy' WHERE slug = 'kr2';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatý kříž 1. třídy', title_instr = 'zlatým křížem 1. třídy' WHERE slug = 'kr1';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'plaketu ČČK', title_instr = 'plaketou ČČK' WHERE slug = 'plk';"
    )

    # SQLite almost does not support ALTER_TABLE :(
    # so we have to create a new one, copy its content,
    # drop the old one and rename the new one to the old name.
    # All of this just to set the new columns to NOT NULL.
    op.create_table(
        "medals_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("minimum_donations", sa.Integer(), nullable=False),
        sa.Column("title_acc", sa.String(), nullable=False),
        sa.Column("title_instr", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.execute("INSERT INTO medals_new SELECT * FROM medals;")
    op.drop_table("medals")
    op.rename_table("medals_new", "medals")


def downgrade():
    op.drop_column("medals", "title_acc")
    op.drop_column("medals", "title_instr")
