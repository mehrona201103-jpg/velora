"""Promo codes API."""
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, String, Integer, Numeric, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.deps import DbSession, require_permissions, CurrentUser
from app.core.exceptions import NotFoundError, ValidationError
from app.models.user import User

router = APIRouter()


class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromoCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    discount_type: str = Field(..., pattern="^(percent|fixed)$")
    discount_value: Decimal = Field(..., gt=0)
    min_order_amount: Decimal | None = None
    max_uses: int | None = None


class PromoOut(BaseModel):
    id: int
    code: str
    discount_type: str
    discount_value: Decimal
    is_active: bool

    class Config:
        from_attributes = True


class PromoValidate(BaseModel):
    code: str
    order_amount: Decimal = Field(..., ge=0)


class PromoValidateResult(BaseModel):
    valid: bool
    discount: Decimal = Decimal("0")
    message: str = ""


@router.post("", response_model=PromoOut, status_code=201)
async def create_promo(
    data: PromoCreate,
    db: DbSession,
    admin: User = Depends(require_permissions("promotions.manage")),
):
    existing = await db.execute(select(PromoCode).where(PromoCode.code == data.code.upper()))
    if existing.scalar_one_or_none():
        from app.core.exceptions import ConflictError
        raise ConflictError("Промокод уже существует")
    promo = PromoCode(
        code=data.code.upper(),
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        min_order_amount=data.min_order_amount,
        max_uses=data.max_uses,
        is_active=True,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return PromoOut.model_validate(promo)


@router.post("/validate", response_model=PromoValidateResult)
async def validate_promo(data: PromoValidate, db: DbSession):
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == data.code.upper(), PromoCode.is_active == True)  # noqa
    )
    promo = result.scalar_one_or_none()
    if not promo:
        return PromoValidateResult(valid=False, message="Промокод не найден")
    now = datetime.now(timezone.utc)
    if promo.valid_from and promo.valid_from > now:
        return PromoValidateResult(valid=False, message="Промокод ещё не активен")
    if promo.valid_to and promo.valid_to < now:
        return PromoValidateResult(valid=False, message="Промокод истёк")
    if promo.max_uses is not None and promo.used_count >= promo.max_uses:
        return PromoValidateResult(valid=False, message="Лимит использований исчерпан")
    if promo.min_order_amount and data.order_amount < promo.min_order_amount:
        return PromoValidateResult(valid=False, message=f"Минимальная сумма заказа: {promo.min_order_amount}")
    if promo.discount_type == "percent":
        discount = (data.order_amount * promo.discount_value / Decimal("100")).quantize(Decimal("0.01"))
    else:
        discount = min(promo.discount_value, data.order_amount)
    return PromoValidateResult(valid=True, discount=discount, message="OK")
