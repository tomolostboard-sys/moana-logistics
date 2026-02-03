from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.db.models.models_v1 import (
    Site,
    Supplier,
    Product,
    Location,
    StockLevel,
    PurchaseOrder,
    PurchaseOrderLine,
    GoodsReceipt,
    GoodsReceiptLine,
)
from backend.app.db.models.core_types import (
    LocationType,
    POStatus,
    ReceiptStatus,
)
from backend.services.procurement import rebuild_qty_on_order


def test_rebuild_qty_on_order_before_po_closed(db_session):
    """
    GIVEN
    - un PO approved de 10 unités
    - une réception POSTED de 5 unités
    - rebuild effectué AVANT fermeture du PO

    THEN
    - qty_on_order == 5

    Note: test hermétique (crée son propre site/supplier/product) pour éviter
    toute pollution de la DB locale moana.
    """

    # IDs uniques pour éviter toute collision avec ta DB existante
    seed = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    SITE_ID = 9_000_000_000_000 + seed
    SUPPLIER_ID = 8_000_000_000_000 + seed
    PRODUCT_ID = 7_000_000_000_000 + seed

    now = datetime.now(timezone.utc)

    # ---------- ARRANGE : master data ----------
    # Site
    if not db_session.get(Site, SITE_ID):
        db_session.add(Site(id=SITE_ID, name=f"TEST-SITE-{SITE_ID}", timezone="Pacific/Tahiti", active=True))

    # Supplier
    if not db_session.get(Supplier, SUPPLIER_ID):
        db_session.add(Supplier(id=SUPPLIER_ID, name=f"TEST-SUP-{SUPPLIER_ID}", country="PF", lead_time_days=1, reliability_score=80))

    # Product
    if not db_session.get(Product, PRODUCT_ID):
        db_session.add(Product(id=PRODUCT_ID, sku=f"TEST-SKU-{PRODUCT_ID}", name=f"TEST-PROD-{PRODUCT_ID}", uom="unit", active=True))

    db_session.flush()

    # Location DOCK du site de test (name TAH-DOCK pour matcher la convention)
    dock = db_session.execute(
        select(Location).where(
            Location.site_id == SITE_ID,
            Location.type == LocationType.dock,
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

    # StockLevel initial (optionnel, mais ça rend le test explicite)
    sl = db_session.execute(
        select(StockLevel).where(
            StockLevel.product_id == PRODUCT_ID,
            StockLevel.location_id == dock.id,
        )
    ).scalar_one_or_none()
    if not sl:
        db_session.add(
            StockLevel(
                product_id=PRODUCT_ID,
                location_id=dock.id,
                qty_on_hand=0,
                qty_reserved=0,
                qty_on_order=0,
            )
        )

    # Purchase Order (APPROVED) + line 10
    po = PurchaseOrder(
        po_number=f"TEST-PO-{SITE_ID}-{seed}",
        supplier_id=SUPPLIER_ID,
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

    # Goods Receipt POSTED (5 reçues)
    gr = GoodsReceipt(
        po_id=po.id,
        site_id=SITE_ID,
        status=ReceiptStatus.posted,
        received_at=now,
        received_by=1,
        idempotency_key=f"test-gr-{SITE_ID}-{seed}",
    )
    db_session.add(gr)
    db_session.flush()

    db_session.add(
        GoodsReceiptLine(
            receipt_id=gr.id,
            product_id=PRODUCT_ID,
            qty_received=5,
            qty_damaged=0,
        )
    )

    db_session.commit()

    # ---------- ACT ----------
    rebuild_qty_on_order(
        db_session,
        site_id=SITE_ID,
        product_ids=[PRODUCT_ID],
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
