"""Order models and state machine statuses."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    Numeric,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


# Allowed order statuses (strict state machine)
ORDER_STATUSES = (
    "CREATED",
    "PAYMENT_PENDING",
    "PAID",
    "CONFIRMED",
    "PREPARING",
    "READY_FOR_PICKUP",
    "ASSIGNED",
    "COURIER_ACCEPTED",
    "PICKED_UP",
    "ON_THE_WAY",
    "ARRIVED",
    "DELIVERED",
    "COMPLETED",
    "CANCELLED",
    "EXPIRED",
    "REFUND_REQUESTED",
    "REFUNDED",
)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="CREATED", nullable=False, index=True)
    delivery_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PICKUP | DELIVERY
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TJS")
    promo_code: Mapped[str | None] = mapped_column(String(50))
    # Delivery address
    city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[str | None] = mapped_column(String(30))
    longitude: Mapped[str | None] = mapped_column(String(30))
    # Pickup
    pickup_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qr_code: Mapped[str | None] = mapped_column(String(100))
    # Meta
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    delivery: Mapped["Delivery | None"] = relationship(back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


from app.models.delivery import Delivery  # noqa: E402
