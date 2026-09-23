"""Admin orders management."""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, require_permissions
from app.core.exceptions import NotFoundError
from app.models.order import Order, OrderItem
from app.models.user import User
from app.services.order import OrderService

router = APIRouter()


class OrderItemOut(BaseModel):
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    class Config:
        from_attributes = True


class AdminOrderOut(BaseModel):
    id: int
    order_number: str
    user_id: int
    status: str
    delivery_type: str
    total: Decimal
    currency: str
    city: str | None
    address: str | None
    phone: str | None
    created_at: datetime
    items: list[OrderItemOut] = []

    class Config:
        from_attributes = True


class PaginatedAdminOrders(BaseModel):
    items: list[AdminOrderOut]
    total: int
    page: int
    per_page: int


@router.get("", response_model=PaginatedAdminOrders)
async def admin_list_orders(
    db: DbSession,
    admin: User = Depends(require_permissions("orders.read")),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    q = select(Order)
    cq = select(func.count(Order.id))
    if status:
        q = q.where(Order.status == status)
        cq = cq.where(Order.status == status)
    total = (await db.execute(cq)).scalar() or 0
    result = await db.execute(
        q.options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    orders = result.scalars().all()
    items = [
        AdminOrderOut(
            id=o.id, order_number=o.order_number, user_id=o.user_id, status=o.status,
            delivery_type=o.delivery_type, total=o.total, currency=o.currency,
            city=o.city, address=o.address, phone=o.phone, created_at=o.created_at,
            items=[OrderItemOut.model_validate(i) for i in o.items],
        )
        for o in orders
    ]
    return PaginatedAdminOrders(items=items, total=total, page=page, per_page=per_page)


class StatusBody(BaseModel):
    status: str


@router.patch("/{order_id}/status", response_model=AdminOrderOut)
async def admin_set_status(
    order_id: int,
    data: StatusBody,
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
    return AdminOrderOut(
        id=order.id, order_number=order.order_number, user_id=order.user_id,
        status=order.status, delivery_type=order.delivery_type, total=order.total,
        currency=order.currency, city=order.city, address=order.address,
        phone=order.phone, created_at=order.created_at,
        items=[OrderItemOut.model_validate(i) for i in order.items],
    )
