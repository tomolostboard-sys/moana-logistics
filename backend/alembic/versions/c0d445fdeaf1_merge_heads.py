"""merge heads

Revision ID: c0d445fdeaf1
Revises: 1664c43728fc, xxxxxxxxxxxx
Create Date: 2026-01-30 09:03:40.687192

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0d445fdeaf1'
down_revision: Union[str, Sequence[str], None] = ('1664c43728fc', 'xxxxxxxxxxxx')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
