from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    Numeric,
    Text,
    Enum,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.db.models.core_types import (
    Role,
    LocationType,
    MovementType,
    POStatus,
    ShipmentMode,
    ShipmentStatus,
    ReceiptStatus,
)

# ---------- MASTER DATA ----------
class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Pacific/Tahiti", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[LocationType] = mapped_column(Enum(LocationType, name="location_type"), nullable=False)

    site: Mapped[Site] = relationship()
    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_location_site_name"),)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    uom: Mapped[str] = mapped_column(String(32), default="unit", nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))  # ISO2 optionnel
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    reliability_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)  # 0..100

    __table_args__ = (
        CheckConstraint("reliability_score >= 0 AND reliability_score <= 100", name="ck_supplier_reliability_0_100"),
        CheckConstraint("lead_time_days >= 0", name="ck_supplier_lead_time_nonneg"),
    )


# ---------- AUTH ----------
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    site: Mapped[Site] = relationship()


# ---------- PROCUREMENT / INBOUND ----------
class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mode: Mapped[ShipmentMode] = mapped_column(Enum(ShipmentMode, name="shipment_mode"), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(128))
    tracking_ref: Mapped[str | None] = mapped_column(String(128), index=True)
    origin: Mapped[str | None] = mapped_column(String(128))
    destination: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, name="shipment_status"),
        default=ShipmentStatus.booked,
        nullable=False,
    )
    eta_initial: Mapped[date | None] = mapped_column(Date)
    eta_current: Mapped[date | None] = mapped_column(Date)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    events: Mapped[list["ShipmentEvent"]] = relationship(back_populates="shipment", cascade="all, delete-orphan")
    containers: Mapped[list["Container"]] = relationship(back_populates="shipment", cascade="all, delete-orphan")


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_code: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128))
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="MANUAL", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="events")

    __table_args__ = (Index("ix_shipment_events_ship_time", "shipment_id", "event_time"),)


class Container(Base):
    __tablename__ = "containers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    container_number: Mapped[str] = mapped_column(String(16), nullable=False)
    seal_number: Mapped[str | None] = mapped_column(String(32))
    type: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="IN_TRANSIT", nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="containers")

    __table_args__ = (UniqueConstraint("container_number", name="uq_container_number"),)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    po_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[POStatus] = mapped_column(Enum(POStatus, name="po_status"), default=POStatus.draft, nullable=False)

    expected_eta: Mapped[date | None] = mapped_column(Date)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey("shipments.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    supplier: Mapped[Supplier] = relationship()
    site: Mapped[Site] = relationship()
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(back_populates="po", cascade="all, delete-orphan")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True)
    qty_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    po: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()

    __table_args__ = (
        CheckConstraint("qty_ordered > 0", name="ck_po_line_qty_pos"),
        CheckConstraint("unit_cost >= 0", name="ck_po_line_unit_cost_nonneg"),
    )


class ASN(Base):
    __tablename__ = "asn"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    po_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    expected_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    po_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False)

    status: Mapped[ReceiptStatus] = mapped_column(
        Enum(ReceiptStatus, name="receipt_status"),
        default=ReceiptStatus.draft,
        nullable=False,
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    container_id: Mapped[int | None] = mapped_column(ForeignKey("containers.id", ondelete="SET NULL"))

    # Idempotence receipt (clé unique, nullable OK)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    lines: Mapped[list["GoodsReceiptLine"]] = relationship(back_populates="receipt", cascade="all, delete-orphan")


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"
    receipt_id: Mapped[int] = mapped_column(ForeignKey("goods_receipts.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True)
    qty_received: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_damaged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lot_code: Mapped[str | None] = mapped_column(String(64))
    expiration_date: Mapped[date | None] = mapped_column(Date)

    receipt: Mapped[GoodsReceipt] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()

    __table_args__ = (
        CheckConstraint("qty_received >= 0", name="ck_gr_line_qty_received_nonneg"),
        CheckConstraint("qty_damaged >= 0", name="ck_gr_line_qty_damaged_nonneg"),
    )


# ---------- INVENTORY ----------
class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))
    to_location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))

    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType, name="movement_type"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))

    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_movement_qty_pos"),
        Index("ix_stock_movements_product_time", "product_id", "happened_at"),
    )


class StockLevel(Base):
    __tablename__ = "stock_levels"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), primary_key=True)

    qty_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qty_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qty_on_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("qty_on_hand >= 0", name="ck_stock_on_hand_nonneg"),
        CheckConstraint("qty_reserved >= 0", name="ck_stock_reserved_nonneg"),
        CheckConstraint("qty_on_order >= 0", name="ck_stock_on_order_nonneg"),
        CheckConstraint("qty_reserved <= qty_on_hand", name="ck_stock_reserved_le_on_hand"),
    )


# ---------- AUDIT ----------
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)
