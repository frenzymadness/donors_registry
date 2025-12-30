"""new table for ContactImportLog model

Revision ID: c4944a5dd4a0
Revises: 56b8d32bbc2a
Create Date: 2025-12-30 10:58:45.856019

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4944a5dd4a0"
down_revision = "56b8d32bbc2a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contact_import_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("imported_by_user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("processed_lines_count", sa.Integer(), nullable=False),
        sa.Column("created_notes_count", sa.Integer(), nullable=False),
        sa.Column("updated_notes_count", sa.Integer(), nullable=False),
        sa.Column("emails_added_count", sa.Integer(), nullable=False),
        sa.Column("phones_added_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["imported_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("contact_import_logs")
