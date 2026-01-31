from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import StockLevel, Location, Product
from backend.app.schemas.stock_level import StockLevelRead

router = APIRouter(prefix="/stock")


@router.get(
    "",
    response_model=list[StockLevelRead],
)
def get_stock(
    site_id: int | None = None,
    location_id: int | None = None,
    product_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    Stock (READ ONLY)
    - qty_on_order est calculé, jamais modifiable
    - exposition sécurisée via schema Pydantic
    """

    stmt = (
        select(StockLevel)
        .join(Location, Location.id == StockLevel.location_id)
        .join(Product, Product.id == StockLevel.product_id)
        .order_by(Location.site_id, StockLevel.location_id, Product.sku)
    )

    if site_id is not None:
        stmt = stmt.where(Location.site_id == site_id)

    if location_id is not None:
        stmt = stmt.where(StockLevel.location_id == location_id)

    if product_id is not None:
        stmt = stmt.where(StockLevel.product_id == product_id)

    stock_levels = db.execute(stmt).scalars().all()
    return stock_levels
