from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import Supplier

router = APIRouter(prefix="/suppliers")


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str | None = Field(default=None, max_length=2)
    lead_time_days: int = Field(default=14, ge=0)
    reliability_score: int = Field(default=70, ge=0, le=100)


@router.get("")
def list_suppliers(db: Session = Depends(get_db)):
    rows = db.execute(select(Supplier).order_by(Supplier.name)).scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "country": s.country,
            "lead_time_days": s.lead_time_days,
            "reliability_score": s.reliability_score,
        }
        for s in rows
    ]


@router.post("")
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    exists = db.execute(select(Supplier).where(Supplier.name == payload.name)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Supplier already exists")

    s = Supplier(
        name=payload.name,
        country=payload.country,
        lead_time_days=payload.lead_time_days,
        reliability_score=payload.reliability_score,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name}
