"""Update names of medals

Revision ID: e1f6598ba415
Revises: 60a681c463a2
Create Date: 2023-04-26 08:35:05.689006

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e1f6598ba415"
down_revision = "60a681c463a2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE medals SET title_acc = 'bronzovou medaili Prof. MUDr. Jana Janského', title_instr = 'bronzovou medailí Prof. MUDr. Jana Janského' WHERE slug = 'br';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'stříbrnou medaili Prof. MUDr. Jana Janského', title_instr = 'stříbrnou medailí Prof. MUDr. Jana Janského' WHERE slug = 'st';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatou medaili Prof. MUDr. Jana Janského', title_instr = 'zlatou medailí Prof. MUDr. Jana Janského' WHERE slug = 'zl';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatý kříž ČČK 3. třídy', title_instr = 'zlatým křížem ČČK 3. třídy' WHERE slug = 'kr3';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatý kříž ČČK 2. třídy', title_instr = 'zlatým křížem ČČK 2. třídy' WHERE slug = 'kr2';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'zlatý kříž ČČK 1. třídy', title_instr = 'zlatým křížem ČČK 1. třídy' WHERE slug = 'kr1';"
    )
    op.execute(
        "UPDATE medals SET title_acc = 'plaketu ČČK Dar krve - dar života', title_instr = 'plaketou ČČK Dar krve - dar života' WHERE slug = 'plk';"
    )


def downgrade():
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
