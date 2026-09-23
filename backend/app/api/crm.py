"""CRM / VIP levels API."""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.deps import DbSession, require_permissions, CurrentUser
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.finance import Balance

router = APIRouter()


class VipLevel(Base):
    __tablename__ = "vip_levels"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    min_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CustomerNote(Base):
    __tablename__ = "customer_notes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VipLevelOut(BaseModel):
    id: int
    name: str
    min_spent: Decimal
    discount_percent: Decimal

    class Config:
        from_attributes = True


class VipCreate(BaseModel):
    name: str
    min_spent: Decimal = Field(default=Decimal("0"), ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    sort_order: int = 0


class CustomerOut(BaseModel):
    id: int
    phone: str
    first_name: str
    last_name: str
    balance: Decimal
    is_active: bool
    roles: list[str] = []


class NoteCreate(BaseModel):
    text: str = Field(..., min_length=1)


class NoteOut(BaseModel):
    id: int
    user_id: int
    author_id: int
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/vip-levels", response_model=list[VipLevelOut])
async def list_vip(db: DbSession):
    result = await db.execute(select(VipLevel).where(VipLevel.is_active == True).order_by(VipLevel.sort_order))  # noqa
    return [VipLevelOut.model_validate(v) for v in result.scalars().all()]


@router.post("/vip-levels", response_model=VipLevelOut, status_code=201)
async def create_vip(
    data: VipCreate,
    db: DbSession,
    admin: User = Depends(require_permissions("crm.manage")),
):
    v = VipLevel(
        name=data.name,
        min_spent=data.min_spent,
        discount_percent=data.discount_percent,
        sort_order=data.sort_order,
        is_active=True,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return VipLevelOut.model_validate(v)


@router.get("/customers", response_model=list[CustomerOut])
async def list_customers(
    db: DbSession,
    admin: User = Depends(require_permissions("crm.manage")),
    q: str | None = None,
    limit: int = Query(50, le=200),
):
    query = select(User).order_by(User.created_at.desc()).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    out = []
    for u in users:
        if q and q.lower() not in (u.phone or "").lower() and q.lower() not in (u.first_name or "").lower():
            continue
        bal = await db.execute(select(Balance).where(Balance.user_id == u.id))
        b = bal.scalar_one_or_none()
        out.append(CustomerOut(
            id=u.id, phone=u.phone, first_name=u.first_name, last_name=u.last_name,
            balance=b.amount if b else Decimal("0"), is_active=u.is_active,
            roles=[r.name for r in u.roles] if u.roles else [],
        ))
    return out


@router.post("/customers/{user_id}/notes", response_model=NoteOut, status_code=201)
async def add_note(
    user_id: int,
    data: NoteCreate,
    db: DbSession,
    admin: User = Depends(require_permissions("crm.manage")),
):
    target = await db.execute(select(User).where(User.id == user_id))
    if not target.scalar_one_or_none():
        raise NotFoundError("Клиент не найден")
    note = CustomerNote(user_id=user_id, author_id=admin.id, text=data.text)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteOut.model_validate(note)


@router.get("/customers/{user_id}/notes", response_model=list[NoteOut])
async def list_notes(
    user_id: int,
    db: DbSession,
    admin: User = Depends(require_permissions("crm.manage")),
):
    result = await db.execute(
        select(CustomerNote).where(CustomerNote.user_id == user_id).order_by(CustomerNote.created_at.desc())
    )
    return [NoteOut.model_validate(n) for n in result.scalars().all()]
