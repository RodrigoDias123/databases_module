"""contract: drop customer.email and the sync trigger

Revision ID: 0005_contract_email
Revises: 0004_expand_email_address
Create Date: 2026-10-30

Run only after version 1 of the API is stopped: it is the last code that reads or writes email.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_contract_email"
down_revision: Union[str, Sequence[str], None] = "0004_expand_email_address"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TRIGGER customer_sync_email ON customer")
    op.execute("DROP FUNCTION customer_sync_email()")
    op.drop_column("customer", "email")


def downgrade() -> None:
    """Back to the state after 0004: email filled from email_address, and the trigger."""
    op.add_column("customer", sa.Column("email", sa.Text(), nullable=True))
    # Same function as in 0004. A migration does not import another one: each stays as it was
    # when it was written.
    op.execute(
        """
        CREATE FUNCTION customer_sync_email() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.email_address IS NULL THEN
                    NEW.email_address := NEW.email;
                ELSIF NEW.email IS NULL THEN
                    NEW.email := NEW.email_address;
                END IF;
            ELSIF NEW.email IS DISTINCT FROM OLD.email
                  AND NEW.email_address IS NOT DISTINCT FROM OLD.email_address THEN
                NEW.email_address := NEW.email;
            ELSIF NEW.email_address IS DISTINCT FROM OLD.email_address
                  AND NEW.email IS NOT DISTINCT FROM OLD.email THEN
                NEW.email := NEW.email_address;
            END IF;
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER customer_sync_email
        BEFORE INSERT OR UPDATE OF email, email_address ON customer
        FOR EACH ROW EXECUTE FUNCTION customer_sync_email()
        """
    )
    op.execute("UPDATE customer SET email = email_address")
