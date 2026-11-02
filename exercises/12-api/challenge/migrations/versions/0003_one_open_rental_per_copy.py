"""rental_one_open_per_copy: at most one open rental per copy

Revision ID: 0003_one_open_rental_per_copy
Revises: 0002_loyalty_points
Create Date: 2026-10-30

On a fresh Pagila, copies 1358, 1435 and 2408 have two open rentals each, and the unique
index cannot be created over them. The older open rental of each copy is closed first, with
return_date = rental_date of the newer one: the copy came back when it was rented again.

The downgrade drops the index only. The data fix stays (see README).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_one_open_rental_per_copy"
down_revision: Union[str, Sequence[str], None] = "0002_loyalty_points"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Every open rental except the newest of its copy is closed at the next open rental's date.
    # With lead() this also works if a copy has more than two open rentals.
    op.execute(
        """
        WITH open_rental AS (
            SELECT rental_id,
                   lead(rental_date) OVER (
                       PARTITION BY inventory_id ORDER BY rental_date, rental_id
                   ) AS next_rental_date
            FROM rental
            WHERE return_date IS NULL
        )
        UPDATE rental r
        SET return_date = o.next_rental_date
        FROM open_rental o
        WHERE r.rental_id = o.rental_id
          AND o.next_rental_date IS NOT NULL
        """
    )
    op.create_index(
        "rental_one_open_per_copy",
        "rental",
        ["inventory_id"],
        unique=True,
        postgresql_where=sa.text("return_date IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("rental_one_open_per_copy", table_name="rental")
