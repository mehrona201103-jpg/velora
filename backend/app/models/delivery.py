"""Delivery and Courier models."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    Boolean,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Courier(Base):
    __tablename__ = "couriers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OFFLINE")  # ONLINE, OFFLINE, BUSY, PAUSED
    vehicle_type: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    locations: Mapped[list["CourierLocation"]] = relationship(back_populates="courier")


class CourierLocation(Base):
    __tablename__ = "courier_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    courier_id: Mapped[int] = mapped_column(ForeignKey("couriers.id", ondelete="CASCADE"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    courier: Mapped[Courier] = relationship(back_populates="locations")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("couriers.id"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    courier_earning: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="delivery")


from app.models.order import Order  # noqa: E402
