"""add stock_levels nonneg constraints

Revision ID: 11dc41ad9497
Revises: e73747d5c5af
Create Date: 2026-02-03
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "11dc41ad9497"
down_revision: Union[str, Sequence[str], None] = "e73747d5c5af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "stock_levels"

CK_ON_HAND = "ck_stock_on_hand_nonneg"
CK_RESERVED = "ck_stock_reserved_nonneg"
CK_ON_ORDER = "ck_stock_on_order_nonneg"


def _add_check_if_missing(constraint_name: str, check_sql: str) -> None:
    # Idempotent Postgres
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = '{TABLE_NAME}'
                  AND c.conname = '{constraint_name}'
            ) THEN
                ALTER TABLE {TABLE_NAME}
                ADD CONSTRAINT {constraint_name}
                CHECK ({check_sql});
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    # --- SAFETY FIX (si des données existantes sont déjà sales)
    # On corrige le minimum pour ne pas faire échouer la migration.
    # Si tu préfères "fail hard", on peut enlever ces UPDATE.
    op.execute(
        f"""
        UPDATE {TABLE_NAME}
        SET qty_on_hand = 0
        WHERE qty_on_hand < 0;
        """
    )
    op.execute(
        f"""
        UPDATE {TABLE_NAME}
        SET qty_reserved = 0
        WHERE qty_reserved < 0;
        """
    )
    op.execute(
        f"""
        UPDATE {TABLE_NAME}
        SET qty_on_order = 0
        WHERE qty_on_order < 0;
        """
    )
    # Si jamais reserved > on_hand, on clamp (tu as déjà une contrainte e737, mais on sécurise)
    op.execute(
        f"""
        UPDATE {TABLE_NAME}
        SET qty_reserved = qty_on_hand
        WHERE qty_reserved > qty_on_hand;
        """
    )

    # --- ADD CHECKS
    _add_check_if_missing(CK_ON_HAND, "qty_on_hand >= 0")
    _add_check_if_missing(CK_RESERVED, "qty_reserved >= 0")
    _add_check_if_missing(CK_ON_ORDER, "qty_on_order >= 0")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {TABLE_NAME} DROP CONSTRAINT IF EXISTS {CK_ON_ORDER};")
    op.execute(f"ALTER TABLE {TABLE_NAME} DROP CONSTRAINT IF EXISTS {CK_RESERVED};")
    op.execute(f"ALTER TABLE {TABLE_NAME} DROP CONSTRAINT IF EXISTS {CK_ON_HAND};")
