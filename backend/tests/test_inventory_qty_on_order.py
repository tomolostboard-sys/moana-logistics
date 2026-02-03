from datetime import datetime

from sqlalchemy import select

from backend.app.db.models.models_v1 import (
    StockLevel,
    PurchaseOrder,
    PurchaseOrderLine,
    GoodsReceipt,
    GoodsReceiptLine,
    Location,
)
from backend.app.db.models.core_types import POStatus, LocationType
from backend.app.services.procurement import rebuild_qty_on_order


def test_rebuild_qty_on_order_before_po_closed(db_session):
    """
    GIVEN
    - un PO approved de 10 unités
    - une réception de 5 unités
    - rebuild effectué AVANT fermeture du PO

    THEN
    - qty_on_order == 5
    """

    SITE_ID = 1
    PRODUCT_ID = 1

    # ---------- ARRANGE ----------

    # Location DOCK
    dock = db_session.execute(
        select(Location).where(
            Location.site_id == SITE_ID,
            Location.type == LocationType.dock,
        )
    ).scalar_one_or_none()

    if not dock:
        dock = Location(
            site_id=SITE_ID,
            name="TAH-DOCK",
            type=LocationType.dock,
        )
        db_session.add(dock)
        db_session.flush()

    # Purchase Order
    po = PurchaseOrder(
        po_number=f"TEST-PO-{datetime.utcnow().timestamp()}",
        supplier_id=1,
        site_id=SITE_ID,
        status=POStatus.approved,
    )
    db_session.add(po)
    db_session.flush()

    db_session.add(
        PurchaseOrderLine(
            po_id=po.id,
            product_id=PRODUCT_ID,
            qty_ordered=10,
            unit_cost=100,
        )
    )

    # Goods Receipt (5 units received)
    gr = GoodsReceipt(
        site_id=SITE_ID,
        received_at=datetime.utcnow(),
    )
    db_session.add(gr)
    db_session.flush()

    db_session.add(
        GoodsReceiptLine(
            receipt_id=gr.id,
            product_id=PRODUCT_ID,
            quantity=5,
        )
    )

    db_session.commit()

    # ---------- ACT ----------

    rebuild_qty_on_order(
        db_session,
        product_id=PRODUCT_ID,
        site_id=SITE_ID,
    )
    db_session.commit()

    # ---------- ASSERT ----------

    sl = db_session.execute(
        select(StockLevel).where(
            StockLevel.product_id == PRODUCT_ID,
            StockLevel.location_id == dock.id,
        )
    ).scalar_one()

    assert sl.qty_on_order == 5
