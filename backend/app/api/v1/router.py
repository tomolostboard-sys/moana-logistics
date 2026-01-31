from fastapi import APIRouter

from backend.app.api.v1.endpoints.health import router as health_router
from backend.app.api.v1.endpoints.products import router as products_router
from backend.app.api.v1.endpoints.suppliers import router as suppliers_router
from backend.app.api.v1.endpoints.shipments import router as shipments_router
from backend.app.api.v1.endpoints.purchase_orders import router as purchase_orders_router
from backend.app.api.v1.endpoints.goods_receipts import router as goods_receipts_router
from backend.app.api.v1.endpoints.locations import router as locations_router
from backend.app.api.v1.endpoints.stock import router as stock_router
from backend.app.api.v1.endpoints.stock_movements import router as stock_movements_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(products_router, tags=["products"])
router.include_router(suppliers_router, tags=["suppliers"])
router.include_router(shipments_router, tags=["shipments"])
router.include_router(purchase_orders_router, tags=["purchase_orders"])
router.include_router(goods_receipts_router, tags=["goods_receipts"])
router.include_router(locations_router, tags=["locations"])
router.include_router(stock_router, tags=["stock"])
router.include_router(stock_movements_router, tags=["stock_movements"])
