from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import (
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
    Site,
    Product,
    Shipment,
)
from backend.app.db.models.core_types import POStatus

router = APIRouter(prefix="/purchase-orders")


class POLineCreate(BaseModel):
    product_id: int
    qty_ordered: int = Field(gt=0)
    unit_cost: float = Field(ge=0)


class POCreate(BaseModel):
    po_number: str = Field(min_length=1, max_length=64)
    supplier_id: int
    site_id: int = 1
    expected_eta: date | None = None
    shipment_id: int | None = None
    lines: list[POLineCreate] = Field(default_factory=list)


@router.get("")
def list_pos(db: Session = Depends(get_db)):
    rows = db.execute(select(PurchaseOrder).order_by(PurchaseOrder.id.desc())).scalars().all()
    return [
        {
            "id": po.id,
            "po_number": po.po_number,
            "supplier_id": po.supplier_id,
            "site_id": po.site_id,
            "status": po.status,
            "expected_eta": po.expected_eta,
            "shipment_id": po.shipment_id,
            "created_at": po.created_at,
        }
        for po in rows
    ]


@router.get("/{po_id}")
def get_po(po_id: int, db: Session = Depends(get_db)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    lines = (
        db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po_id))
        .scalars()
        .all()
    )
    return {
        "id": po.id,
        "po_number": po.po_number,
        "supplier_id": po.supplier_id,
        "site_id": po.site_id,
        "status": po.status,
        "expected_eta": po.expected_eta,
        "shipment_id": po.shipment_id,
        "created_at": po.created_at,
        "lines": [
            {
                "product_id": l.product_id,
                "qty_ordered": l.qty_ordered,
                "unit_cost": float(l.unit_cost),
            }
            for l in lines
        ],
    }


@router.post("")
def create_po(payload: POCreate, db: Session = Depends(get_db)):
    # Unique PO number
    exists = db.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == payload.po_number)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="PO number already exists")

    # FK checks (fail fast, message clair)
    if not db.get(Supplier, payload.supplier_id):
        raise HTTPException(status_code=400, detail="Invalid supplier_id")
    if not db.get(Site, payload.site_id):
        raise HTTPException(status_code=400, detail="Invalid site_id")
    if payload.shipment_id is not None and not db.get(Shipment, payload.shipment_id):
        raise HTTPException(status_code=400, detail="Invalid shipment_id")

    # Validate products in lines
    for ln in payload.lines:
        if not db.get(Product, ln.product_id):
            raise HTTPException(status_code=400, detail=f"Invalid product_id {ln.product_id}")

    po = PurchaseOrder(
        po_number=payload.po_number,
        supplier_id=payload.supplier_id,
        site_id=payload.site_id,
        status=POStatus.draft,
        expected_eta=payload.expected_eta,
        shipment_id=payload.shipment_id,
    )
    db.add(po)
    db.flush()  # get po.id

    for ln in payload.lines:
        db.add(
            PurchaseOrderLine(
                po_id=po.id,
                product_id=ln.product_id,
                qty_ordered=ln.qty_ordered,
                unit_cost=ln.unit_cost,
            )
        )

    db.commit()
    db.refresh(po)
    return {"id": po.id, "po_number": po.po_number}
