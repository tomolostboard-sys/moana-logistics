from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    StockLevel,
    StockMovement,
    Location,
)
from backend.app.db.models.core_types import MovementType, ReceiptStatus
from backend.app.services.inventory import rebuild_qty_on_order

router = APIRouter(prefix="/goods-receipts")


class GRLineCreate(BaseModel):
    product_id: int
    qty_received: int = Field(gt=0)


class GRCreate(BaseModel):
    po_id: int
    received_at: datetime
    to_location_id: int
    lines: list[GRLineCreate] = Field(default_factory=list)


def _ensure_location(db: Session, location_id: int) -> Location:
    loc = db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=400, detail="Invalid to_location_id")
    return loc


def _make_receipt_idempotency_key(payload: GRCreate, site_id: int, provided: str | None) -> str:
    """
    1) Si le client fournit Idempotency-Key header -> stable et robuste.
    2) Sinon: clé dérivée du payload (retry exact = même clé).
    """
    if provided and provided.strip():
        raw = f"GR-IDEMP:{site_id}:{provided.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    lines = sorted([(ln.product_id, ln.qty_received) for ln in payload.lines], key=lambda x: x[0])
    raw = f"GR:{site_id}:{payload.po_id}:{payload.to_location_id}:{payload.received_at.isoformat()}:{lines}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _make_movement_idempotency_key(
    receipt_key: str,
    product_id: int,
    to_location_id: int,
    received_at: datetime,
    qty: int,
) -> str:
    raw = f"GRMOVE:{receipt_key}:{product_id}:{to_location_id}:{received_at.isoformat()}:{qty}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("")
def create_goods_receipt(
    payload: GRCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    try:
        po = db.get(PurchaseOrder, payload.po_id)
        if not po:
            raise HTTPException(status_code=404, detail="PO not found")

        loc = _ensure_location(db, payload.to_location_id)
        if loc.site_id != po.site_id:
            raise HTTPException(status_code=400, detail="to_location_id is not in the PO site")

        po_lines = (
            db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po.id))
            .scalars()
            .all()
        )
        po_product_ids = {l.product_id for l in po_lines}
        for ln in payload.lines:
            if ln.product_id not in po_product_ids:
                raise HTTPException(status_code=400, detail=f"product_id {ln.product_id} not in PO")

        receipt_key = _make_receipt_idempotency_key(payload, site_id=int(po.site_id), provided=idempotency_key)

        # ✅ Fast path: receipt déjà créé -> return direct (pas de double stock)
        existing = db.execute(
            select(GoodsReceipt).where(GoodsReceipt.idempotency_key == receipt_key)
        ).scalar_one_or_none()
        if existing:
            return {"id": existing.id, "po_id": existing.po_id, "to_location_id": payload.to_location_id}

        # ✅ On crée un receipt POSTED directement (sinon qty_on_order devient incohérent)
        gr = GoodsReceipt(
            po_id=po.id,
            site_id=po.site_id,
            status=ReceiptStatus.posted,
            received_at=payload.received_at,
            received_by=1,  # TODO: user courant
            idempotency_key=receipt_key,
        )
        db.add(gr)

        # Concurrence: si deux requêtes arrivent en même temps
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing = db.execute(
                select(GoodsReceipt).where(GoodsReceipt.idempotency_key == receipt_key)
            ).scalar_one()
            return {"id": existing.id, "po_id": existing.po_id, "to_location_id": payload.to_location_id}

        for ln in payload.lines:
            db.add(
                GoodsReceiptLine(
                    receipt_id=gr.id,
                    product_id=ln.product_id,
                    qty_received=ln.qty_received,
                    qty_damaged=0,
                )
            )

            sl = (
                db.execute(
                    select(StockLevel).where(
                        StockLevel.product_id == ln.product_id,
                        StockLevel.location_id == payload.to_location_id,
                    )
                )
                .scalar_one_or_none()
            )

            if not sl:
                sl = StockLevel(
                    product_id=ln.product_id,
                    location_id=payload.to_location_id,
                    qty_on_hand=0,
                    qty_reserved=0,
                    qty_on_order=0,
                )
                db.add(sl)
                db.flush()

            sl.qty_on_hand += ln.qty_received

            move_key = _make_movement_idempotency_key(
                receipt_key=receipt_key,
                product_id=ln.product_id,
                to_location_id=payload.to_location_id,
                received_at=payload.received_at,
                qty=ln.qty_received,
            )

            db.add(
                StockMovement(
                    product_id=ln.product_id,
                    from_location_id=None,
                    to_location_id=payload.to_location_id,
                    movement_type=MovementType.receipt,
                    quantity=ln.qty_received,
                    reason="GOODS_RECEIPT",
                    happened_at=payload.received_at,
                    created_by=1,  # TODO: user courant
                    idempotency_key=move_key,
                )
            )

        # ✅ Rebuild qty_on_order dans la même transaction
        product_ids = [ln.product_id for ln in payload.lines]
        rebuild_qty_on_order(db, site_id=int(po.site_id), product_ids=product_ids)

        db.commit()
        return {"id": gr.id, "po_id": po.id, "to_location_id": payload.to_location_id}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
