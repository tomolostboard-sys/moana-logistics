"""add stock_levels reserved <= on_hand constraint

Revision ID: e73747d5c5af
Revises: c0d445fdeaf1
Create Date: 2026-01-31 08:14:34.921717
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e73747d5c5af"
down_revision: Union[str, Sequence[str], None] = "c0d445fdeaf1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_stock_reserved_le_on_hand"
TABLE_NAME = "stock_levels"


def upgrade() -> None:
    # Idempotent en Postgres (évite les surprises si tu rejoues/merges)
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = '{TABLE_NAME}'
              AND c.conname = '{CONSTRAINT_NAME}'
        ) THEN
            ALTER TABLE {TABLE_NAME}
            ADD CONSTRAINT {CONSTRAINT_NAME}
            CHECK (qty_reserved <= qty_on_hand);
        END IF;
    END $$;
    """)


def downgrade() -> None:
    # Downgrade safe: IF EXISTS sinon tu te reprends l'erreur "does not exist"
    op.execute(f"""
    ALTER TABLE {TABLE_NAME}
    DROP CONSTRAINT IF EXISTS {CONSTRAINT_NAME};
    """)
