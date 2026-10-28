from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class OrderStatus(str, enum.Enum):
    created = "created"
    awaiting_payment = "awaiting_payment"
    payment_review = "payment_review"
    paid = "paid"
    processing = "processing"
    ordered_from_supplier = "ordered_from_supplier"
    in_transit = "in_transit"
    arrived_in_tajikistan = "arrived_in_tajikistan"
    ready_for_pickup = "ready_for_pickup"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    return_requested = "return_requested"
    refunded = "refunded"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    awaiting_review = "awaiting_review"
    paid = "paid"
    rejected = "rejected"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.awaiting_payment, index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.unpaid, index=True)

    # Snapshot of prices at order time (never change later)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Address snapshot
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_city: Mapped[str] = mapped_column(String(100))
    delivery_phone: Mapped[str | None] = mapped_column(String(32))
    delivery_zone_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_zones.id"), nullable=True)
    delivery_notes: Mapped[str | None] = mapped_column(Text)
    # none | quoted | accepted | rejected
    delivery_quote_status: Mapped[str] = mapped_column(String(20), default="none")

    payment_method_id: Mapped[int | None] = mapped_column(ForeignKey("payment_methods.id"), nullable=True)
    payment_rejection_reason: Mapped[str | None] = mapped_column(Text)

    customer_comment: Mapped[str | None] = mapped_column(Text)
    admin_comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payment_submissions: Mapped[list["PaymentSubmission"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)

    # Snapshot
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(150))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    order: Mapped["Order"] = relationship(back_populates="status_history")


from app.models.user import User  # noqa: E402
from app.models.payment import PaymentSubmission  # noqa: E402
