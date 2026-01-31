from alembic import op
import sqlalchemy as sa


# Remplace par tes IDs réels
revision = "xxxxxxxxxxxx"
down_revision = None  # ou ta révision précédente
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_stock_reserved_le_on_hand",
        "stock_levels",
        "qty_reserved <= qty_on_hand",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_stock_reserved_le_on_hand",
        "stock_levels",
        type_="check",
    )
