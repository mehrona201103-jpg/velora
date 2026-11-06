from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.order import CartItemAdd, CartOut, CartItemOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/cart", tags=["cart"])


def get_or_create_cart(db: Session, user: User) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


@router.get("", response_model=CartOut)
def get_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = get_or_create_cart(db, user)
    items = db.query(CartItem).options(
        joinedload(CartItem.product).joinedload(Product.images),
        joinedload(CartItem.variant),
    ).filter(CartItem.cart_id == cart.id).all()

    result_items = []
    subtotal = Decimal("0")
    for item in items:
        p = item.product
        if not p:
            continue
        price = p.final_price
        if item.variant:
            price += item.variant.price_modifier
        total = price * item.quantity
        subtotal += total
        img = next((i.url for i in p.images if i.is_main), p.images[0].url if p.images else None)
        result_items.append(CartItemOut(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            product_name=p.name_ru,
            unit_price=price,
            total_price=total,
            image_url=img,
        ))

    return CartOut(
        id=cart.id,
        items=result_items,
        subtotal=subtotal,
        items_count=sum(i.quantity for i in result_items),
    )


@router.post("/items", response_model=CartOut)
def add_to_cart(data: CartItemAdd, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == data.product_id, Product.is_published == True).first()
    if not product:
        raise HTTPException(404, "Product not found")
    if product.stock < data.quantity:
        raise HTTPException(400, "Not enough stock")

    if data.variant_id:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == data.variant_id,
            ProductVariant.product_id == product.id,
            ProductVariant.is_active == True,
        ).first()
        if not variant:
            raise HTTPException(400, "Variant not found")
        if variant.stock < data.quantity:
            raise HTTPException(400, "Not enough stock for variant")

    cart = get_or_create_cart(db, user)
    existing = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == data.product_id,
        CartItem.variant_id == data.variant_id,
    ).first()

    if existing:
        existing.quantity += data.quantity
    else:
        existing = CartItem(
            cart_id=cart.id,
            product_id=data.product_id,
            variant_id=data.variant_id,
            quantity=data.quantity,
        )
        db.add(existing)
    db.commit()
    return get_cart(db, user)


@router.patch("/items/{item_id}")
def update_cart_item(item_id: int, quantity: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = get_or_create_cart(db, user)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if quantity <= 0:
        db.delete(item)
    else:
        item.quantity = quantity
    db.commit()
    return get_cart(db, user)


@router.delete("/items/{item_id}")
def remove_cart_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = get_or_create_cart(db, user)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()
    return get_cart(db, user)


@router.delete("")
def clear_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = get_or_create_cart(db, user)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return {"ok": True}
