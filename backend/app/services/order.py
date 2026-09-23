"""Order service with strict state machine."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationError, NotFoundError, InsufficientBalanceError, OutOfStockError
from app.models.order import Order, OrderItem, ORDER_STATUSES
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.finance import Balance, BalanceTransaction
from app.models.inventory import InventoryReservation
from app.services.inventory import InventoryService

# Valid transitions
TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"PAYMENT_PENDING", "PAID", "CANCELLED"},
    "PAYMENT_PENDING": {"PAID", "CANCELLED", "EXPIRED"},
    "PAID": {"CONFIRMED", "CANCELLED", "REFUND_REQUESTED"},
    "CONFIRMED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"READY_FOR_PICKUP", "ASSIGNED", "CANCELLED"},
    "READY_FOR_PICKUP": {"COMPLETED", "EXPIRED", "CANCELLED"},
    "ASSIGNED": {"COURIER_ACCEPTED", "CANCELLED"},
    "COURIER_ACCEPTED": {"PICKED_UP", "CANCELLED"},
    "PICKED_UP": {"ON_THE_WAY"},
    "ON_THE_WAY": {"ARRIVED"},
    "ARRIVED": {"DELIVERED"},
    "DELIVERED": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "EXPIRED": {"REFUND_REQUESTED"},
    "REFUND_REQUESTED": {"REFUNDED", "CANCELLED"},
    "REFUNDED": set(),
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory = InventoryService(db)

    def _validate_transition(self, current: str, new: str) -> None:
        allowed = TRANSITIONS.get(current, set())
        if new not in allowed:
            raise ValidationError(f"Недопустимый переход статуса: {current} → {new}")

    async def transition(self, order: Order, new_status: str, actor_id: int | None = None) -> Order:
        self._validate_transition(order.status, new_status)
        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return order

    async def checkout_from_cart(
        self,
        user_id: int,
        delivery_type: str,
        *,
        city: str | None = None,
        district: str | None = None,
        address: str | None = None,
        phone: str | None = None,
        comment: str | None = None,
        latitude: str | None = None,
        longitude: str | None = None,
        idempotency_key: str | None = None,
        delivery_fee: Decimal = Decimal("0.00"),
    ) -> Order:
        if delivery_type not in ("PICKUP", "DELIVERY"):
            raise ValidationError("delivery_type должен быть PICKUP или DELIVERY")

        if idempotency_key:
            existing = await self.db.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
            if existing.scalar_one_or_none():
                raise ValidationError("Заказ с таким ключом уже создан")

        # Load cart
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()
        if not cart or not cart.items:
            raise ValidationError("Корзина пуста")

        # Validate items & calculate
        subtotal = Decimal("0.00")
        line_items: list[dict] = []
        for item in cart.items:
            var_result = await self.db.execute(
                select(ProductVariant)
                .options(selectinload(ProductVariant.product))
                .where(ProductVariant.id == item.variant_id, ProductVariant.is_active == True)  # noqa
            )
            variant = var_result.scalar_one_or_none()
            if not variant or not variant.product or not variant.product.is_active:
                raise ValidationError(f"Товар недоступен (variant {item.variant_id})")

            price = variant.price_override or variant.product.base_price
            line_total = price * item.quantity
            subtotal += line_total
            line_items.append({
                "variant": variant,
                "quantity": item.quantity,
                "unit_price": price,
                "total_price": line_total,
                "product_name": variant.product.name_ru,
                "sku": variant.sku,
            })

        total = subtotal + delivery_fee

        # Check balance
        bal_result = await self.db.execute(
            select(Balance).where(Balance.user_id == user_id).with_for_update()
        )
        balance = bal_result.scalar_one_or_none()
        if not balance or balance.amount < total:
            raise InsufficientBalanceError("Недостаточно средств на балансе")

        # Reserve inventory
        reservations: list[InventoryReservation] = []
        try:
            for li in line_items:
                res = await self.inventory.reserve(
                    variant_id=li["variant"].id,
                    quantity=li["quantity"],
                    user_id=user_id,
                    ttl_minutes=60,
                )
                reservations.append(res)
        except OutOfStockError:
            for r in reservations:
                await self.inventory.release(r.id)
            raise

        # Debit balance
        before = balance.amount
        balance.amount = before - total
        after = balance.amount

        # Create order
        order_number = f"VEL-{int(datetime.now(timezone.utc).timestamp())}"
        pickup_expires = None
        qr_code = None
        if delivery_type == "PICKUP":
            pickup_expires = datetime.now(timezone.utc) + timedelta(days=5)
            qr_code = order_number

        order = Order(
            order_number=order_number,
            user_id=user_id,
            status="PAID",
            delivery_type=delivery_type,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            discount=Decimal("0.00"),
            total=total,
            city=city,
            district=district,
            address=address,
            phone=phone,
            comment=comment,
            latitude=latitude,
            longitude=longitude,
            pickup_expires_at=pickup_expires,
            qr_code=qr_code,
            idempotency_key=idempotency_key,
        )
        self.db.add(order)
        await self.db.flush()

        for li in line_items:
            oi = OrderItem(
                order_id=order.id,
                variant_id=li["variant"].id,
                product_name=li["product_name"],
                sku=li["sku"],
                quantity=li["quantity"],
                unit_price=li["unit_price"],
                total_price=li["total_price"],
            )
            self.db.add(oi)

        # Link reservations to order
        for r in reservations:
            r.order_id = order.id

        # Balance transaction
        tx = BalanceTransaction(
            balance_id=balance.id,
            user_id=user_id,
            amount=total,
            type="DEBIT",
            reference_type="order",
            reference_id=order.id,
            balance_before=before,
            balance_after=after,
            actor_id=user_id,
            description=f"Оплата заказа {order_number}",
        )
        self.db.add(tx)

        # Clear cart
        for item in list(cart.items):
            await self.db.delete(item)

        await self.db.flush()
        return order
