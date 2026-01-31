import enum

class Role(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    field = "field"

class LocationType(str, enum.Enum):
    warehouse = "warehouse"
    zone = "zone"
    dock = "dock"
    customs = "customs"
    quarantine = "quarantine"
    store = "store"

class MovementType(str, enum.Enum):
    receipt = "RECEIPT"
    issue = "ISSUE"
    transfer = "TRANSFER"
    adjustment = "ADJUSTMENT"
    scrap = "SCRAP"
    reserve = "RESERVE"
    unreserve = "UNRESERVE"

class POStatus(str, enum.Enum):
    draft = "DRAFT"
    approved = "APPROVED"
    shipped = "SHIPPED"
    partial = "PARTIAL"
    closed = "CLOSED"
    cancelled = "CANCELLED"

class ShipmentMode(str, enum.Enum):
    sea = "SEA"
    air = "AIR"

class ShipmentStatus(str, enum.Enum):
    booked = "BOOKED"
    departed = "DEPARTED"
    in_transit = "IN_TRANSIT"
    arrived = "ARRIVED"
    customs = "CUSTOMS"
    out_for_delivery = "OUT_FOR_DELIVERY"
    delivered = "DELIVERED"

class ReceiptStatus(str, enum.Enum):
    draft = "DRAFT"
    posted = "POSTED"
    cancelled = "CANCELLED"
