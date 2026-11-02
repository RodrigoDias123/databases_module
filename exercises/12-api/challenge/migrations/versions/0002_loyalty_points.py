"""customer.loyalty_points: one point per rental

Revision ID: 0002_loyalty_points
Revises: 0001_baseline
Create Date: 2026-10-30

Three steps, so the column never exists as NOT NULL without a value:
1. add it as nullable (no rewrite of the table, existing rows get NULL);
2. fill it with each customer's number of rentals;
3. set NOT NULL, with server_default 0 for the rows inserted from now on.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_loyalty_points"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("loyalty_points", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE customer c
        SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)
        """
    )
    op.alter_column("customer", "loyalty_points", nullable=False, server_default=sa.text("0"))


def downgrade() -> None:
    op.drop_column("customer", "loyalty_points")
