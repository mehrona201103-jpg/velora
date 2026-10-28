from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from decimal import Decimal


class Role(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    support = "support"
    courier = "courier"
    customer = "customer"


class DeviceType(str, enum.Enum):
    phone = "phone"
    tablet = "tablet"
    pc = "pc"


class VerificationStatus(str, enum.Enum):
    none = "none"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.customer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    device_type: Mapped[str] = mapped_column(String(20), default="phone")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    verification_status: Mapped[str] = mapped_column(String(20), default="none", index=True)
    verification_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_age_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_passport_selfie: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_passport_front: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    lock_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    referral_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True, index=True)
    referred_by: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    addresses: Mapped[list["UserAddress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    cart: Mapped["Cart | None"] = relationship(back_populates="user", uselist=False)
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100), default="Дом")
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100))
    street: Mapped[str | None] = mapped_column(String(255))
    house: Mapped[str | None] = mapped_column(String(50))
    apartment: Mapped[str | None] = mapped_column(String(50))
    full_address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="addresses")


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="favorites")
    product: Mapped["Product"] = relationship()


from app.models.order import Order  # noqa: E402
from app.models.cart import Cart  # noqa: E402
from app.models.product import Product  # noqa: E402
