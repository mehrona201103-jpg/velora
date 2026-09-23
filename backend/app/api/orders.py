"""Orders API — checkout and order management."""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, require_permissions
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.core.config import get_settings
from app.models.order import Order, OrderItem
from app.models.user import User
from app.services.order import OrderService

router = APIRouter()
settings = get_settings()


class CheckoutRequest(BaseModel):
    delivery_type: str = Field(..., pattern="^(PICKUP|DELIVERY)$")
    city: str | None = None
    district: str | None = None
    address: str | None = None
    phone: str | None = None
    comment: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    idempotency_key: str | None = None


class OrderItemOut(BaseModel):
    id: int
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    order_number: str
    status: str
    delivery_type: str
    subtotal: Decimal
    delivery_fee: Decimal
    discount: Decimal
    total: Decimal
    currency: str
    city: str | None
    address: str | None
    phone: str | None
    qr_code: str | None
    pickup_expires_at: datetime | None
    created_at: datetime
    items: list[OrderItemOut] = []

    class Config:
        from_attributes = True


class PaginatedOrders(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    per_page: int


@router.post("/checkout", response_model=OrderOut, status_code=201)
async def checkout(data: CheckoutRequest, user: CurrentUser, db: DbSession):
    if data.delivery_type == "DELIVERY":
        if not data.address:
            raise ValidationError("Для доставки укажите адрес")
        delivery_fee = Decimal(settings.default_delivery_fee)
    else:
        delivery_fee = Decimal("0.00")

    service = OrderService(db)
    order = await service.checkout_from_cart(
        user_id=user.id,
        delivery_type=data.delivery_type,
        city=data.city,
        district=data.district,
        address=data.address,
        phone=data.phone or user.phone,
        comment=data.comment,
        latitude=data.latitude,
        longitude=data.longitude,
        idempotency_key=data.idempotency_key,
        delivery_fee=delivery_fee,
    )
    await db.commit()

    # Reload with items
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    order = result.scalar_one()
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        delivery_type=order.delivery_type,
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount=order.discount,
        total=order.total,
        currency=order.currency,
        city=order.city,
        address=order.address,
        phone=order.phone,
        qr_code=order.qr_code,
        pickup_expires_at=order.pickup_expires_at,
        created_at=order.created_at,
        items=[OrderItemOut.model_validate(i) for i in order.items],
    )


@router.get("", response_model=PaginatedOrders)
async def list_my_orders(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
):
    from sqlalchemy import func
    count_q = select(func.count(Order.id)).where(Order.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(q)
    orders = result.scalars().all()

    items = [
        OrderOut(
            id=o.id,
            order_number=o.order_number,
            status=o.status,
            delivery_type=o.delivery_type,
            subtotal=o.subtotal,
            delivery_fee=o.delivery_fee,
            discount=o.discount,
            total=o.total,
            currency=o.currency,
            city=o.city,
            address=o.address,
            phone=o.phone,
            qr_code=o.qr_code,
            pickup_expires_at=o.pickup_expires_at,
            created_at=o.created_at,
            items=[OrderItemOut.model_validate(i) for i in o.items],
        )
        for o in orders
    ]
    return PaginatedOrders(items=items, total=total, page=page, per_page=per_page)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Заказ не найден")
    # Client can only see own orders unless admin
    is_staff = any(r.name in ("ADMIN", "OWNER") for r in user.roles)
    if order.user_id != user.id and not is_staff:
        raise ForbiddenError("Нет доступа к этому заказу")
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        delivery_type=order.delivery_type,
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount=order.discount,
        total=order.total,
        currency=order.currency,
        city=order.city,
        address=order.address,
        phone=order.phone,
        qr_code=order.qr_code,
        pickup_expires_at=order.pickup_expires_at,
        created_at=order.created_at,
        items=[OrderItemOut.model_validate(i) for i in order.items],
    )


class StatusUpdate(BaseModel):
    status: str


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    data: StatusUpdate,
    db: DbSession,
    admin: User = Depends(require_permissions("orders.write")),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Заказ не найден")

    service = OrderService(db)
    await service.transition(order, data.status, actor_id=admin.id)
    await db.commit()
    await db.refresh(order)

    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        delivery_type=order.delivery_type,
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount=order.discount,
        total=order.total,
        currency=order.currency,
        city=order.city,
        address=order.address,
        phone=order.phone,
        qr_code=order.qr_code,
        pickup_expires_at=order.pickup_expires_at,
        created_at=order.created_at,
        items=[OrderItemOut.model_validate(i) for i in order.items],
    )
