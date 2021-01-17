"""Set proper 'NOT NULL' where needed

Revision ID: 9c829c41652e
Revises: 9c632e7c77df
Create Date: 2021-01-16 12:39:08.741926

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c829c41652e"
down_revision = "9c632e7c77df"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite almost does not support ALTER_TABLE :(
    # so we have to create a new one, copy its content,
    # drop the old one and rename the new one to the old name
    op.create_table(
        "medals_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("minimum_donations", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.execute("INSERT INTO medals_new SELECT * FROM medals;")
    op.drop_table("medals")
    op.rename_table("medals_new", "medals")

    op.create_table(
        "users_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=80), nullable=False),
        sa.Column("password", sa.LargeBinary(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.execute("INSERT INTO users_new SELECT * FROM users;")
    op.drop_table("users")
    op.rename_table("users_new", "users")


def downgrade():
    op.create_table(
        "medals_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("minimum_donations", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.execute("INSERT INTO medals_new SELECT * FROM medals;")
    op.drop_table("medals")
    op.rename_table("medals_new", "medals")

    op.create_table(
        "users_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=80), nullable=False),
        sa.Column("password", sa.LargeBinary(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.execute("INSERT INTO users_new SELECT * FROM users;")
    op.drop_table("users")
    op.rename_table("users_new", "users")
