"""baseline: the Pagila schema as it already exists

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-30

Empty on purpose. The tables already exist, so this revision only gives them a place in the
history: `alembic stamp head` writes it to alembic_version without running anything, and
`alembic downgrade base` stops here without dropping them.
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
