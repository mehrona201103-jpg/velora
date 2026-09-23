"""Courier panel API."""
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, require_roles, require_permissions
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.models.delivery import Courier, CourierLocation, Delivery
from app.models.order import Order
from app.models.user import User
from app.services.order import OrderService

router = APIRouter()


class CourierStatusBody(BaseModel):
    status: str = Field(..., pattern="^(ONLINE|OFFLINE|BUSY|PAUSED)$")


class LocationBody(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class CourierOut(BaseModel):
    id: int
    status: str
    is_active: bool
    vehicle_type: str | None

    class Config:
        from_attributes = True


class DeliveryJobOut(BaseModel):
    delivery_id: int
    order_id: int
    order_number: str
    status: str
    address: str | None
    phone: str | None
    total: Decimal

    class Config:
        from_attributes = True


async def _get_courier(db, user_id: int) -> Courier:
    result = await db.execute(select(Courier).where(Courier.user_id == user_id))
    c = result.scalar_one_or_none()
    if not c:
        raise ForbiddenError("Вы не зарегистрированы как курьер")
    return c


@router.post("/me/register", response_model=CourierOut, status_code=201)
async def register_as_courier(
    db: DbSession,
    admin: User = Depends(require_permissions("couriers.manage")),
    user_id: int = 0,
):
    """Admin creates courier profile for a user. Pass user_id in query via body alternative."""
    raise ValidationError("Используйте POST /api/v1/couriers/create")


class CreateCourierBody(BaseModel):
    user_id: int
    vehicle_type: str | None = None


@router.post("/create", response_model=CourierOut, status_code=201)
async def create_courier(
    data: CreateCourierBody,
    db: DbSession,
    admin: User = Depends(require_permissions("couriers.manage")),
):
    existing = await db.execute(select(Courier).where(Courier.user_id == data.user_id))
    if existing.scalar_one_or_none():
        from app.core.exceptions import ConflictError
        raise ConflictError("Курьер уже существует")
    c = Courier(user_id=data.user_id, status="OFFLINE", vehicle_type=data.vehicle_type, is_active=True)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CourierOut.model_validate(c)


@router.get("/me", response_model=CourierOut)
async def my_courier_profile(user: CurrentUser, db: DbSession):
    c = await _get_courier(db, user.id)
    return CourierOut.model_validate(c)


@router.patch("/me/status", response_model=CourierOut)
async def set_courier_status(data: CourierStatusBody, user: CurrentUser, db: DbSession):
    c = await _get_courier(db, user.id)
    c.status = data.status
    await db.commit()
    await db.refresh(c)
    return CourierOut.model_validate(c)


@router.post("/me/location")
async def update_location(data: LocationBody, user: CurrentUser, db: DbSession):
    c = await _get_courier(db, user.id)
    loc = CourierLocation(
        courier_id=c.id,
        latitude=data.latitude,
        longitude=data.longitude,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(loc)
    await db.commit()
    return {"ok": True}


@router.get("/me/jobs", response_model=list[DeliveryJobOut])
async def my_jobs(user: CurrentUser, db: DbSession):
    c = await _get_courier(db, user.id)
    result = await db.execute(
        select(Delivery).where(Delivery.courier_id == c.id).order_by(Delivery.created_at.desc()).limit(50)
    )
    deliveries = result.scalars().all()
    out = []
    for d in deliveries:
        o_res = await db.execute(select(Order).where(Order.id == d.order_id))
        order = o_res.scalar_one_or_none()
        if order:
            out.append(DeliveryJobOut(
                delivery_id=d.id, order_id=order.id, order_number=order.order_number,
                status=d.status, address=order.address, phone=order.phone, total=order.total,
            ))
    return out


@router.post("/me/jobs/{delivery_id}/accept")
async def accept_job(delivery_id: int, user: CurrentUser, db: DbSession):
    c = await _get_courier(db, user.id)
    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id, Delivery.courier_id == c.id))
    d = result.scalar_one_or_none()
    if not d:
        raise NotFoundError("Заявка не найдена")
    d.status = "ACCEPTED"
    d.accepted_at = datetime.now(timezone.utc)
    o_res = await db.execute(select(Order).where(Order.id == d.order_id))
    order = o_res.scalar_one_or_none()
    if order:
        service = OrderService(db)
        try:
            await service.transition(order, "COURIER_ACCEPTED", actor_id=user.id)
        except Exception:
            pass
    await db.commit()
    return {"ok": True, "status": "ACCEPTED"}


@router.post("/me/jobs/{delivery_id}/complete")
async def complete_job(delivery_id: int, user: CurrentUser, db: DbSession):
    c = await _get_courier(db, user.id)
    result = await db.execute(select(Delivery).where(Delivery.id == delivery_id, Delivery.courier_id == c.id))
    d = result.scalar_one_or_none()
    if not d:
        raise NotFoundError("Заявка не найдена")
    d.status = "COMPLETED"
    d.delivered_at = datetime.now(timezone.utc)
    o_res = await db.execute(select(Order).where(Order.id == d.order_id))
    order = o_res.scalar_one_or_none()
    if order:
        service = OrderService(db)
        for st in ("PICKED_UP", "ON_THE_WAY", "ARRIVED", "DELIVERED", "COMPLETED"):
            try:
                if order.status != st:
                    await service.transition(order, st, actor_id=user.id)
            except Exception:
                continue
    await db.commit()
    return {"ok": True, "status": "COMPLETED"}
