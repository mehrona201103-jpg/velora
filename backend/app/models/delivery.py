from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    free_from_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_days_min: Mapped[int] = mapped_column(Integer, default=1)
    estimated_days_max: Mapped[int] = mapped_column(Integer, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_type: Mapped[str] = mapped_column(String(50), default="home")  # home | pickup | self
    instructions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DeliveryRate(Base):
    """Optional weight-based or extra rates. For simplicity zones hold base price."""
    __tablename__ = "delivery_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("delivery_zones.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    min_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    max_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    extra_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
