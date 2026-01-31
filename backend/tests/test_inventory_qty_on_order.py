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
from backend.app.db.models.core_types import POStatus, ReceiptStatus, LocationType
from backend.app.services.inventory import rebuild_qty_on_order


def test_rebuild_qty_on_order_before_po_closed(db_session):
    """
    GIVEN
    - un PO approved de 10 unités
    - une réception POSTED de 5 unités
    - rebuild effectué AVANT fermeture du PO

    THEN
    - qty_on_order == 5
    """

    SITE_ID = 1
    PRODUCT_ID = 1

    # ---------- ARRANGE ----------

    # Location DOCK (get or create)
    dock = db_session.execute(
        select(Location).where(
            Location.site_id == SITE_ID,
            Location.name == "TAH-DOCK",
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

    # Stock level initial
    sl = db_session.execute(
        select(StockLevel).where(
            StockLevel.product_id == PRODUCT_ID,
            StockLevel.location_id == dock.id,
        )
    ).scalar_one_or_none()

    if not sl:
        sl = StockLevel(
            product_id=PRODUCT_ID,
            location_id=dock.id,
            qty_on_hand=0,
            qty_reserved=0,
        )
        db_session.add(sl)

    # Purchase Order (VALIDE)
    po = PurchaseOrder(
        po_number=f"TEST-PO-{datetime.utcnow().timestamp()}",
        supplier_id=1,
        site_id=SITE_ID,
        status=POStatus.approved,
    )
    db_session.add(po)
    db_session.flush()

    # Purchase Order Line (unit_cost obligatoire)
    po_line = PurchaseOrderLine(
        po_id=po.id,
        product_id=PRODUCT_ID,
        qty_ordered=10,
        unit_cost=100,
    )
    db_session.add(po_line)

    # Goods Receipt POSTED (5 unités)
    gr = GoodsReceipt(
        po_id=po.id,
        site_id=SITE_ID,
        status=ReceiptStatus.posted,
        received_at=datetime.utcnow(),
        received_by=1,
        idempotency_key=f"test-gr-{po.id}",
    )
    db_session.add(gr)
    db_session.flush()

    gr_line = GoodsReceiptLine(
        receipt_id=gr.id,
        product_id=PRODUCT_ID,
        qty_received=5,
        qty_damaged=0,
    )
    db_session.add(gr_line)

    db_session.commit()

    # ---------- ACT ----------

    # Rebuild AVANT fermeture du PO (règle métier)
    rebuild_qty_on_order(db_session, site_id=SITE_ID, product_ids=[PRODUCT_ID])
    db_session.commit()

    # Puis fermeture du PO
    po.status = POStatus.closed
    db_session.commit()

    # ---------- ASSERT ----------

    sl = db_session.execute(
        select(StockLevel).where(
            StockLevel.product_id == PRODUCT_ID,
            StockLevel.location_id == dock.id,
        )
    ).scalar_one()

    assert sl.qty_on_order == 5
