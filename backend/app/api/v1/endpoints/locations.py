from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.models.models_v1 import Location

router = APIRouter(prefix="/locations")


@router.get("")
def list_locations(
    site_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Location).order_by(Location.site_id, Location.id)
    if site_id is not None:
        stmt = stmt.where(Location.site_id == site_id)

    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": l.id,
            "site_id": l.site_id,
            "name": l.name,
            "type": getattr(l, "type", None),
        }
        for l in rows
    ]
