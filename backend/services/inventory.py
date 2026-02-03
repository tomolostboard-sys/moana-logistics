from __future__ import annotations

from typing import Iterable

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.app.db.models.models_v1 import (
    Location,
    StockLevel,
    PurchaseOrder,
    PurchaseOrderLine,
    GoodsReceipt,
    GoodsReceiptLine,
)
from backend.app.db.models.core_types import LocationType, POStatus, ReceiptStatus


# PO réellement engagés dans le "on order"
ENGAGED_PO_STATUSES = {
    POStatus.approved,
    POStatus.shipped,
    POStatus.partial,
}


def get_inbound_dock_location_id(db: Session, site_id: int) -> int:
    loc = (
        db.execute(
            select(Location)
            .where(Location.site_id == site_id)
            .where(Location.type == LocationType.dock)
            .where(Location.name == "TAH-DOCK")
        )
        .scalars()
        .first()
    )
    if loc:
        return int(loc.id)

    loc = (
        db.execute(
            select(Location)
            .where(Location.site_id == site_id)
            .where(Location.type == LocationType.dock)
            .order_by(Location.id.asc())
        )
        .scalars()
        .first()
    )
    if not loc:
        raise ValueError("No inbound DOCK location found for this site")

    return int(loc.id)


def rebuild_qty_on_order(
    db: Session,
    *,
    site_id: int,
    product_ids: Iterable[int],
) -> None:
    """
    qty_on_order =
        SUM(qty_ordered on engaged PO)
        - SUM(qty_received - qty_damaged on POSTED receipts)

    ⚠️ IMPORTANT :
    - le REÇU dépend UNIQUEMENT des receipts POSTED
    - PAS du statut du PO
    """

    product_ids = sorted({int(pid) for pid in product_ids if pid is not None})
    if not product_ids:
        return

    dock_location_id = get_inbound_dock_location_id(db, site_id)

    # ---------- COMMANDÉ (lié au statut du PO) ----------
    ordered_rows = db.execute(
        select(
            PurchaseOrderLine.product_id,
            func.coalesce(func.sum(PurchaseOrderLine.qty_ordered), 0).label(
                "ordered_qty"
            ),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.po_id)
        .where(PurchaseOrder.site_id == site_id)
        .where(PurchaseOrder.status.in_(ENGAGED_PO_STATUSES))
        .where(PurchaseOrderLine.product_id.in_(product_ids))
        .group_by(PurchaseOrderLine.product_id)
    ).all()

    # ---------- REÇU (POSTED UNIQUEMENT, INDÉPENDANT DU PO) ----------
    received_rows = db.execute(
        select(
            GoodsReceiptLine.product_id,
            func.coalesce(
                func.sum(
                    GoodsReceiptLine.qty_received
                    - GoodsReceiptLine.qty_damaged
                ),
                0,
            ).label("received_qty"),
        )
        .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptLine.receipt_id)
        .where(GoodsReceipt.site_id == site_id)
        .where(GoodsReceipt.status == ReceiptStatus.posted)
        .where(GoodsReceiptLine.product_id.in_(product_ids))
        .group_by(GoodsReceiptLine.product_id)
    ).all()

    ordered = {int(pid): int(qty) for pid, qty in ordered_rows}
    received = {int(pid): int(qty) for pid, qty in received_rows}

    # ---------- STOCK LEVEL ----------
    for pid in product_ids:
        outstanding = ordered.get(pid, 0) - received.get(pid, 0)
        if outstanding < 0:
            outstanding = 0

        sl = (
            db.execute(
                select(StockLevel)
                .where(StockLevel.product_id == pid)
                .where(StockLevel.location_id == dock_location_id)
                .with_for_update()
            )
            .scalar_one_or_none()
        )

        if not sl:
            sl = StockLevel(
                product_id=pid,
                location_id=dock_location_id,
                qty_on_hand=0,
                qty_reserved=0,
                qty_on_order=0,
            )
            db.add(sl)
            db.flush()

        sl.qty_on_order = outstanding
