from __future__ import annotations

import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import StockLevel, StockMovement, Location
from backend.app.db.models.core_types import MovementType

router = APIRouter(prefix="/stock-movements")


# ---------- Schemas ----------
class TransferCreate(BaseModel):
    product_id: int
    from_location_id: int
    to_location_id: int
    quantity: int = Field(gt=0)
    happened_at: datetime
    reason: str | None = None


class ReserveCreate(BaseModel):
    product_id: int
    location_id: int
    quantity: int = Field(gt=0)
    happened_at: datetime
    reason: str | None = None


class IssueCreate(BaseModel):
    product_id: int
    location_id: int
    quantity: int = Field(gt=0)
    happened_at: datetime
    reason: str | None = None


# ---------- Helpers ----------
def _require_idempotency_key(idempotency_key: str | None) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key header")
    return idempotency_key.strip()


def _get_or_create_stock_level(db: Session, product_id: int, location_id: int) -> StockLevel:
    sl = (
        db.execute(
            select(StockLevel)
            .where(StockLevel.product_id == product_id)
            .where(StockLevel.location_id == location_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if sl:
        return sl

    sl = StockLevel(
        product_id=product_id,
        location_id=location_id,
        qty_on_hand=0,
        qty_reserved=0,
        qty_on_order=0,
    )
    db.add(sl)
    db.flush()
    return sl


def _find_existing_movement(db: Session, idem: str) -> StockMovement | None:
    return db.execute(select(StockMovement).where(StockMovement.idempotency_key == idem)).scalar_one_or_none()


# ---------- Endpoints ----------
@router.post("/transfer")
def transfer_stock(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    idem = _require_idempotency_key(idempotency_key)

    if payload.from_location_id == payload.to_location_id:
        raise HTTPException(status_code=400, detail="from_location_id and to_location_id must differ")

    # idempotent replay
    existing = _find_existing_movement(db, idem)
    if existing:
        return {"id": int(existing.id), "idempotency_key": existing.idempotency_key}

    # lock stock levels
    src = _get_or_create_stock_level(db, payload.product_id, payload.from_location_id)
    dst = _get_or_create_stock_level(db, payload.product_id, payload.to_location_id)

    available = src.qty_on_hand - src.qty_reserved
    if available < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient available stock (available={available})")

    src.qty_on_hand -= payload.quantity
    dst.qty_on_hand += payload.quantity

    mv = StockMovement(
        product_id=payload.product_id,
        from_location_id=payload.from_location_id,
        to_location_id=payload.to_location_id,
        movement_type=MovementType.transfer,
        quantity=payload.quantity,
        reason=payload.reason,
        happened_at=payload.happened_at,
        created_by=1,
        idempotency_key=idem,
    )
    db.add(mv)
    db.commit()
    return {"id": int(mv.id), "idempotency_key": mv.idempotency_key}


@router.post("/reserve")
def reserve_stock(
    payload: ReserveCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    idem = _require_idempotency_key(idempotency_key)

    existing = _find_existing_movement(db, idem)
    if existing:
        return {"id": int(existing.id), "idempotency_key": existing.idempotency_key}

    sl = _get_or_create_stock_level(db, payload.product_id, payload.location_id)
    available = sl.qty_on_hand - sl.qty_reserved
    if available < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient available stock (available={available})")

    sl.qty_reserved += payload.quantity

    mv = StockMovement(
        product_id=payload.product_id,
        from_location_id=payload.location_id,
        to_location_id=None,
        movement_type=MovementType.reserve,
        quantity=payload.quantity,
        reason=payload.reason,
        happened_at=payload.happened_at,
        created_by=1,
        idempotency_key=idem,
    )
    db.add(mv)
    db.commit()
    return {"id": int(mv.id), "idempotency_key": mv.idempotency_key}


@router.post("/unreserve")
def unreserve_stock(
    payload: ReserveCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    idem = _require_idempotency_key(idempotency_key)

    existing = _find_existing_movement(db, idem)
    if existing:
        return {"id": int(existing.id), "idempotency_key": existing.idempotency_key}

    sl = _get_or_create_stock_level(db, payload.product_id, payload.location_id)
    if sl.qty_reserved < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient reserved stock (reserved={sl.qty_reserved})")

    sl.qty_reserved -= payload.quantity

    mv = StockMovement(
        product_id=payload.product_id,
        from_location_id=payload.location_id,
        to_location_id=None,
        movement_type=MovementType.unreserve,
        quantity=payload.quantity,
        reason=payload.reason,
        happened_at=payload.happened_at,
        created_by=1,
        idempotency_key=idem,
    )
    db.add(mv)
    db.commit()
    return {"id": int(mv.id), "idempotency_key": mv.idempotency_key}


@router.post("/issue")
def issue_stock(
    payload: IssueCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    idem = _require_idempotency_key(idempotency_key)

    existing = _find_existing_movement(db, idem)
    if existing:
        return {"id": int(existing.id), "idempotency_key": existing.idempotency_key}

    sl = _get_or_create_stock_level(db, payload.product_id, payload.location_id)

    # règle simple: on consomme d'abord le réservé (picking)
    if sl.qty_reserved < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Not enough reserved to issue (reserved={sl.qty_reserved})")
    if sl.qty_on_hand < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Not enough on hand to issue (on_hand={sl.qty_on_hand})")

    sl.qty_reserved -= payload.quantity
    sl.qty_on_hand -= payload.quantity

    mv = StockMovement(
        product_id=payload.product_id,
        from_location_id=payload.location_id,
        to_location_id=None,
        movement_type=MovementType.issue,
        quantity=payload.quantity,
        reason=payload.reason,
        happened_at=payload.happened_at,
        created_by=1,
        idempotency_key=idem,
    )
    db.add(mv)
    db.commit()
    return {"id": int(mv.id), "idempotency_key": mv.idempotency_key}
