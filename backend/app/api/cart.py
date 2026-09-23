"""Cart API."""
from decimal import Decimal
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError, ValidationError, OutOfStockError
from app.models.cart import Cart, CartItem
from app.models.product import ProductVariant, Product
from app.models.inventory import Inventory

router = APIRouter()


class CartItemAdd(BaseModel):
    variant_id: int
    quantity: int = Field(1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=0, le=100)


class CartItemOut(BaseModel):
    id: int
    variant_id: int
    quantity: int
    product_name: str | None = None
    sku: str | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    available: int | None = None

    class Config:
        from_attributes = True


class CartOut(BaseModel):
    id: int
    items: list[CartItemOut]
    subtotal: Decimal
    items_count: int


async def _get_or_create_cart(db, user_id: int) -> Cart:
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
        result = await db.execute(
            select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id)
        )
        cart = result.scalar_one()
    return cart


@router.get("", response_model=CartOut)
async def get_cart(user: CurrentUser, db: DbSession):
    cart = await _get_or_create_cart(db, user.id)
    items_out = []
    subtotal = Decimal("0.00")
    for item in cart.items:
        var_r = await db.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.product), selectinload(ProductVariant.inventory))
            .where(ProductVariant.id == item.variant_id)
        )
        variant = var_r.scalar_one_or_none()
        price = Decimal("0.00")
        name = None
        sku = None
        available = 0
        if variant:
            price = variant.price_override or (variant.product.base_price if variant.product else Decimal("0"))
            name = variant.product.name_ru if variant.product else None
            sku = variant.sku
            if variant.inventory:
                available = variant.inventory.quantity - variant.inventory.reserved
        line = price * item.quantity
        subtotal += line
        items_out.append(
            CartItemOut(
                id=item.id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                product_name=name,
                sku=sku,
                unit_price=price,
                total_price=line,
                available=available,
            )
        )
    return CartOut(id=cart.id, items=items_out, subtotal=subtotal, items_count=len(items_out))


@router.post("/items", response_model=CartOut)
async def add_item(data: CartItemAdd, user: CurrentUser, db: DbSession):
    # Validate variant
    var_r = await db.execute(
        select(ProductVariant)
        .options(selectinload(ProductVariant.inventory), selectinload(ProductVariant.product))
        .where(ProductVariant.id == data.variant_id, ProductVariant.is_active == True)  # noqa
    )
    variant = var_r.scalar_one_or_none()
    if not variant or not variant.product or not variant.product.is_active:
        raise NotFoundError("Вариант товара не найден")

    available = 0
    if variant.inventory:
        available = variant.inventory.quantity - variant.inventory.reserved
    if available < data.quantity:
        raise OutOfStockError(f"Недостаточно товара (доступно: {available})")

    cart = await _get_or_create_cart(db, user.id)

    # Existing item?
    existing = next((i for i in cart.items if i.variant_id == data.variant_id), None)
    if existing:
        new_qty = existing.quantity + data.quantity
        if available < new_qty:
            raise OutOfStockError(f"Недостаточно товара (доступно: {available})")
        existing.quantity = new_qty
    else:
        item = CartItem(cart_id=cart.id, variant_id=data.variant_id, quantity=data.quantity)
        db.add(item)

    await db.commit()
    return await get_cart(user, db)


@router.patch("/items/{item_id}", response_model=CartOut)
async def update_item(item_id: int, data: CartItemUpdate, user: CurrentUser, db: DbSession):
    cart = await _get_or_create_cart(db, user.id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise NotFoundError("Позиция не найдена")

    if data.quantity == 0:
        await db.delete(item)
    else:
        # Check stock
        var_r = await db.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.inventory))
            .where(ProductVariant.id == item.variant_id)
        )
        variant = var_r.scalar_one_or_none()
        available = 0
        if variant and variant.inventory:
            available = variant.inventory.quantity - variant.inventory.reserved
        if available < data.quantity:
            raise OutOfStockError(f"Недостаточно товара (доступно: {available})")
        item.quantity = data.quantity

    await db.commit()
    return await get_cart(user, db)


@router.delete("/items/{item_id}", response_model=CartOut)
async def remove_item(item_id: int, user: CurrentUser, db: DbSession):
    cart = await _get_or_create_cart(db, user.id)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise NotFoundError("Позиция не найдена")
    await db.delete(item)
    await db.commit()
    return await get_cart(user, db)


@router.delete("", response_model=CartOut)
async def clear_cart(user: CurrentUser, db: DbSession):
    cart = await _get_or_create_cart(db, user.id)
    for item in list(cart.items):
        await db.delete(item)
    await db.commit()
    return await get_cart(user, db)
