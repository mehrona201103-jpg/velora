"""Inventory reservation service — atomic stock control."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import OutOfStockError, NotFoundError
from app.models.inventory import Inventory, InventoryReservation
from app.models.product import ProductVariant


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_inventory(self, variant_id: int) -> Inventory:
        result = await self.db.execute(
            select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
        )
        inv = result.scalar_one_or_none()
        if not inv:
            inv = Inventory(variant_id=variant_id, quantity=0, reserved=0)
            self.db.add(inv)
            await self.db.flush()
        return inv

    async def reserve(
        self,
        variant_id: int,
        quantity: int,
        user_id: int,
        order_id: int | None = None,
        ttl_minutes: int = 30,
    ) -> InventoryReservation:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        inv = await self.get_or_create_inventory(variant_id)
        available = inv.quantity - inv.reserved
        if available < quantity:
            raise OutOfStockError(f"Недостаточно товара на складе (доступно: {available})")

        inv.reserved += quantity
        reservation = InventoryReservation(
            variant_id=variant_id,
            order_id=order_id,
            user_id=user_id,
            quantity=quantity,
            status="active",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )
        self.db.add(reservation)
        await self.db.flush()
        return reservation

    async def commit(self, reservation_id: int) -> None:
        result = await self.db.execute(
            select(InventoryReservation).where(InventoryReservation.id == reservation_id)
        )
        res = result.scalar_one_or_none()
        if not res or res.status != "active":
            return

        inv = await self.get_or_create_inventory(res.variant_id)
        inv.quantity = max(0, inv.quantity - res.quantity)
        inv.reserved = max(0, inv.reserved - res.quantity)
        res.status = "committed"
        await self.db.flush()

    async def release(self, reservation_id: int) -> None:
        result = await self.db.execute(
            select(InventoryReservation).where(InventoryReservation.id == reservation_id)
        )
        res = result.scalar_one_or_none()
        if not res or res.status != "active":
            return

        inv = await self.get_or_create_inventory(res.variant_id)
        inv.reserved = max(0, inv.reserved - res.quantity)
        res.status = "released"
        await self.db.flush()

    async def release_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(InventoryReservation).where(
                InventoryReservation.status == "active",
                InventoryReservation.expires_at < now,
            )
        )
        expired = result.scalars().all()
        count = 0
        for res in expired:
            inv = await self.get_or_create_inventory(res.variant_id)
            inv.reserved = max(0, inv.reserved - res.quantity)
            res.status = "expired"
            count += 1
        if count:
            await self.db.flush()
        return count
