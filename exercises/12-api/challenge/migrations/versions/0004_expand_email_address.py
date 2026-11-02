"""expand: customer.email_address next to customer.email, kept in sync by a trigger

Revision ID: 0004_expand_email_address
Revises: 0003_one_open_rental_per_copy
Create Date: 2026-10-30

Version 1 of the API (writes email) and version 2 (writes email_address) run at the same time
after this migration. The trigger copies a change made to either column into the other, so each
version sees the writes of the other.

The trigger is created before the backfill: a row written between the two would otherwise be
copied by neither. Here both run in the same transaction, and ADD COLUMN holds an ACCESS
EXCLUSIVE lock on customer until the commit, so no one can write in between anyway.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_expand_email_address"
down_revision: Union[str, Sequence[str], None] = "0003_one_open_rental_per_copy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("email_address", sa.Text(), nullable=True))
    op.execute(
        """
        CREATE FUNCTION customer_sync_email() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                -- Each version sets only its own column: fill the other one.
                IF NEW.email_address IS NULL THEN
                    NEW.email_address := NEW.email;
                ELSIF NEW.email IS NULL THEN
                    NEW.email := NEW.email_address;
                END IF;
            ELSIF NEW.email IS DISTINCT FROM OLD.email
                  AND NEW.email_address IS NOT DISTINCT FROM OLD.email_address THEN
                NEW.email_address := NEW.email;      -- written by version 1
            ELSIF NEW.email_address IS DISTINCT FROM OLD.email_address
                  AND NEW.email IS NOT DISTINCT FROM OLD.email THEN
                NEW.email := NEW.email_address;      -- written by version 2
            END IF;
            -- If an UPDATE changes both columns, it already sets both: nothing to copy.
            RETURN NEW;
        END
        $$
        """
    )
    # BEFORE: the trigger changes NEW, the row that is about to be written, and does not run
    # another UPDATE, so it does not fire itself again.
    op.execute(
        """
        CREATE TRIGGER customer_sync_email
        BEFORE INSERT OR UPDATE OF email, email_address ON customer
        FOR EACH ROW EXECUTE FUNCTION customer_sync_email()
        """
    )
    op.execute("UPDATE customer SET email_address = email")


def downgrade() -> None:
    # email has every change made through version 2 too (the trigger copied it), so dropping
    # email_address loses nothing.
    op.execute("DROP TRIGGER customer_sync_email ON customer")
    op.execute("DROP FUNCTION customer_sync_email()")
    op.drop_column("customer", "email_address")
