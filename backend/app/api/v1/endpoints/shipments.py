from __future__ import annotations

from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import Shipment, ShipmentEvent
from backend.app.db.models.core_types import ShipmentMode, ShipmentStatus

router = APIRouter(prefix="/shipments")


class ShipmentCreate(BaseModel):
    mode: ShipmentMode
    carrier: str | None = Field(default=None, max_length=128)
    tracking_ref: str | None = Field(default=None, max_length=128)
    origin: str | None = Field(default=None, max_length=128)
    destination: str | None = Field(default=None, max_length=128)
    eta_initial: date | None = None
    eta_current: date | None = None


class ShipmentEventCreate(BaseModel):
    event_code: str = Field(min_length=1, max_length=32)
    location: str | None = Field(default=None, max_length=128)
    event_time: datetime
    source: str = Field(default="MANUAL", max_length=32)
    description: str | None = None


@router.get("")
def list_shipments(db: Session = Depends(get_db)):
    rows = db.execute(select(Shipment).order_by(Shipment.id.desc())).scalars().all()
    return [
        {
            "id": s.id,
            "mode": s.mode,
            "carrier": s.carrier,
            "tracking_ref": s.tracking_ref,
            "origin": s.origin,
            "destination": s.destination,
            "status": s.status,
            "eta_initial": s.eta_initial,
            "eta_current": s.eta_current,
            "last_event_at": s.last_event_at,
            "created_at": s.created_at,
        }
        for s in rows
    ]


@router.post("")
def create_shipment(payload: ShipmentCreate, db: Session = Depends(get_db)):
    s = Shipment(
        mode=payload.mode,
        carrier=payload.carrier,
        tracking_ref=payload.tracking_ref,
        origin=payload.origin,
        destination=payload.destination,
        status=ShipmentStatus.booked,
        eta_initial=payload.eta_initial,
        eta_current=payload.eta_current,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id}


@router.get("/{shipment_id}/events")
def list_events(shipment_id: int, db: Session = Depends(get_db)):
    ship = db.get(Shipment, shipment_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Shipment not found")

    rows = (
        db.execute(
            select(ShipmentEvent)
            .where(ShipmentEvent.shipment_id == shipment_id)
            .order_by(ShipmentEvent.event_time.desc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": e.id,
            "event_code": e.event_code,
            "location": e.location,
            "event_time": e.event_time,
            "source": e.source,
            "description": e.description,
        }
        for e in rows
    ]


@router.post("/{shipment_id}/events")
def add_event(shipment_id: int, payload: ShipmentEventCreate, db: Session = Depends(get_db)):
    ship = db.get(Shipment, shipment_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Shipment not found")

    e = ShipmentEvent(
        shipment_id=shipment_id,
        event_code=payload.event_code,
        location=payload.location,
        event_time=payload.event_time,
        source=payload.source,
        description=payload.description,
    )
    db.add(e)

    # Mise à jour "last_event_at" + status (mapping simple, extensible)
    ship.last_event_at = payload.event_time
    code = payload.event_code.upper()

    if code in {"DEPARTED", "SAILED", "FLIGHT_DEPARTED"}:
        ship.status = ShipmentStatus.departed
    elif code in {"IN_TRANSIT"}:
        ship.status = ShipmentStatus.in_transit
    elif code in {"ARRIVED", "LANDED"}:
        ship.status = ShipmentStatus.arrived
    elif code in {"CUSTOMS"}:
        ship.status = ShipmentStatus.customs
    elif code in {"OUT_FOR_DELIVERY"}:
        ship.status = ShipmentStatus.out_for_delivery
    elif code in {"DELIVERED"}:
        ship.status = ShipmentStatus.delivered

    db.commit()
    return {"ok": True}
