from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import Product

router = APIRouter(prefix="/products")


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    uom: str = Field(default="unit", min_length=1, max_length=32)
    barcode: str | None = Field(default=None, max_length=64)
    active: bool = True


@router.get("")
def list_products(db: Session = Depends(get_db)):
    rows = db.execute(select(Product).order_by(Product.sku)).scalars().all()
    return [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "uom": p.uom,
            "barcode": p.barcode,
            "active": p.active,
        }
        for p in rows
    ]


@router.post("")
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    exists = db.execute(select(Product).where(Product.sku == payload.sku)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="SKU already exists")

    p = Product(
        sku=payload.sku,
        name=payload.name,
        uom=payload.uom,
        barcode=payload.barcode,
        active=payload.active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {"id": p.id, "sku": p.sku, "name": p.name}
