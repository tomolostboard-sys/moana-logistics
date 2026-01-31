from pydantic import BaseModel


class StockLevelRead(BaseModel):
    product_id: int
    location_id: int

    qty_on_hand: int
    qty_reserved: int
    qty_on_order: int  # READ ONLY — calculé, jamais écrit

    class Config:
        from_attributes = True
