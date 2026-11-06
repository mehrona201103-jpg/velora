import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from pathlib import Path
import aiofiles

from app.core.database import get_db
from app.services.media_store import save_bytes_db
from app.api.promo import apply_promo
from app.services.telegram import notify_admin
from app.core.config import settings
from app.models.user import User, Role
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.order import Order, OrderItem, OrderStatusHistory, OrderStatus, PaymentStatus
from app.models.payment import PaymentMethod, PaymentSubmission
from app.models.delivery import DeliveryZone
from app.models.settings import AppSetting
from app.schemas.order import OrderCreate, OrderOut, PaymentMethodOut, DeliveryZoneOut
from app.api.deps import get_current_user, require_roles
from app.api.cart import get_or_create_cart

router = APIRouter(prefix="/orders", tags=["orders"])


def generate_order_number() -> str:
    return f"VL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.query(AppSetting).filter(AppSetting.key == key).first()
    return s.value if s and s.value else default


def _normalize_media_url(url: str) -> str:
    """Dropbox/Drive share links → direct file URL."""
    if not url:
        return url
    u = url.strip()
    if "dropbox.com" in u:
        u = u.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        u = u.replace("?dl=0", "").replace("&dl=0", "")
        if "dl=1" not in u:
            u = u + ("&" if "?" in u else "?") + "dl=1"
        u = u.replace("dl.dropboxusercontent.com", "dl.dropboxusercontent.com")
        # classic: dropbox.com/s/xxx/file?dl=0 → dl.dropboxusercontent.com/s/xxx/file
        u = u.replace("dropbox.com/s/", "dl.dropboxusercontent.com/s/")
        u = u.replace("www.dl.dropboxusercontent.com", "dl.dropboxusercontent.com")
    if "drive.google.com" in u and "/file/d/" in u:
        # https://drive.google.com/file/d/ID/view → uc?export=download&id=ID
        try:
            fid = u.split("/file/d/")[1].split("/")[0]
            u = f"https://drive.google.com/uc?export=view&id={fid}"
        except Exception:
            pass
    return u


@router.get("/banners")
def public_banners(db: Session = Depends(get_db)):
    """Слайды главной: JSON в настройке home_banners."""
    import json
    from app.models.settings import AppSetting
    defaults = [
        {"type": "image", "url": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&q=80", "title": "VELORA", "subtitle": "Доставка по Таджикистану"},
        {"type": "image", "url": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&q=80", "title": "VELORA", "subtitle": "Прозрачная оплата и статус заказа"},
    ]
    row = db.query(AppSetting).filter(AppSetting.key == "home_banners").first()
    if not row or not row.value:
        return defaults
    try:
        data = json.loads(row.value)
        if not isinstance(data, list) or not data:
            return defaults
        out = []
        for item in data:
            if not isinstance(item, dict):
                continue
            item = dict(item)
            item["url"] = _normalize_media_url(item.get("url") or "")
            if item["url"]:
                out.append(item)
        return out or defaults
    except Exception:
        return defaults


@router.get("/settings/public")
def public_settings(db: Session = Depends(get_db)):
    keys = [
        "telegram_channel_url", "telegram_admin_dm", "instagram_url",
        "owner_social_url", "social_link_1_label", "social_link_2_label",
        "office_address", "about_text", "live_broadcast",
    ]
    result = {}
    for k in keys:
        result[k] = get_setting(db, k)
    return result


@router.get("/payment-methods", response_model=list[PaymentMethodOut])
def list_payment_methods(db: Session = Depends(get_db)):
    return db.query(PaymentMethod).filter(PaymentMethod.is_active == True).order_by(PaymentMethod.sort_order).all()


ALLOWED_ZONE_NAMES = {"Худжанд", "Гафуров", "Хистеварз", "Овчикалача", "Сартукай", "Унчи", "Бустон"}

@router.get("/delivery-zones", response_model=list[DeliveryZoneOut])
def list_delivery_zones(city: str | None = None, db: Session = Depends(get_db)):
    q = db.query(DeliveryZone).filter(DeliveryZone.is_active == True, DeliveryZone.name.in_(ALLOWED_ZONE_NAMES))
    if city:
        q = q.filter(DeliveryZone.city.ilike(f"%{city}%"))
    return q.all()


@router.post("", response_model=OrderOut)
def create_order(data: OrderCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role in (Role.owner, Role.admin):
        raise HTTPException(400, "Админ-аккаунт не оформляет заказы покупателя")

    order_items_data = []
    subtotal = Decimal("0")

    if data.from_cart:
        cart = get_or_create_cart(db, user)
        items = db.query(CartItem).options(
            joinedload(CartItem.product),
            joinedload(CartItem.variant),
        ).filter(CartItem.cart_id == cart.id).all()
        if not items:
            raise HTTPException(400, "Корзина пуста")
        for item in items:
            product = item.product
            if not product or not product.is_published:
                raise HTTPException(400, f"Товар недоступен")
            if product.stock < item.quantity:
                raise HTTPException(400, f"Недостаточно на складе: {product.name_ru}")
            price = product.final_price
            if item.variant:
                price += item.variant.price_modifier
            total = price * item.quantity
            subtotal += total
            order_items_data.append({
                "product": product, "variant": item.variant,
                "quantity": item.quantity, "unit_price": price, "total_price": total,
            })
    else:
        if not data.product_id:
            raise HTTPException(400, "Укажите товар")
        product = db.query(Product).filter(Product.id == data.product_id, Product.is_published == True).first()
        if not product:
            raise HTTPException(404, "Товар не найден")
        if product.stock < data.quantity:
            raise HTTPException(400, "Недостаточно на складе")
        variant = None
        if data.variant_id:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == data.variant_id,
                ProductVariant.product_id == product.id,
            ).first()
        price = product.final_price
        if variant:
            price += variant.price_modifier
        total = price * data.quantity
        subtotal = total
        order_items_data.append({
            "product": product, "variant": variant,
            "quantity": data.quantity, "unit_price": price, "total_price": total,
        })

    delivery_cost = Decimal("0")
    delivery_address = data.delivery_address or ""
    delivery_city = data.delivery_city or ""
    zone = None

    if data.delivery_type == "office":
        delivery_cost = Decimal("0")
        office = get_setting(db, "office_address", "Магазин VELORA, Худжанд")
        delivery_address = office
        delivery_city = "Худжанд"
    elif data.delivery_zone_id:
        zone = db.query(DeliveryZone).filter(
            DeliveryZone.id == data.delivery_zone_id,
            DeliveryZone.is_active == True,
        ).first()
        if not zone:
            raise HTTPException(400, "Зона доставки недоступна")
        delivery_cost = Decimal("0")  # admin sets after payment
        if zone.free_from_amount and subtotal >= zone.free_from_amount:
            delivery_cost = Decimal("0")
        delivery_city = zone.city
        if not delivery_address:
            delivery_address = f"{zone.city}" + (f", {zone.district}" if zone.district else "")

    if data.delivery_type == "home" and not delivery_address:
        raise HTTPException(400, "Укажите адрес доставки")

    # Payment method
    pm = None
    if data.payment_method_id:
        pm = db.query(PaymentMethod).filter(PaymentMethod.id == data.payment_method_id, PaymentMethod.is_active == True).first()
    elif data.payment_method_code:
        pm = db.query(PaymentMethod).filter(PaymentMethod.code == data.payment_method_code, PaymentMethod.is_active == True).first()

    promo_discount, promo_used = apply_promo(db, getattr(data, "promo_code", None), subtotal)

    # Referral 5% — one-time per granted credit
    referral_discount = Decimal("0")
    used_referral = False
    try:
        left = int(getattr(user, "referral_discount_left", 0) or 0)
        if left > 0 and subtotal > 0:
            referral_discount = (subtotal * Decimal("5") / Decimal("100")).quantize(Decimal("0.01"))
            used_referral = True
    except Exception:
        pass

    # Social subscribe bonus: 2% on first purchase
    social_discount = Decimal("0")
    used_social = False
    try:
        sleft = int(getattr(user, "social_discount_left", 0) or 0)
        if sleft > 0 and subtotal > 0:
            social_discount = (subtotal * Decimal("2") / Decimal("100")).quantize(Decimal("0.01"))
            used_social = True
    except Exception:
        pass

    # Don't stack discounts beyond subtotal
    total_discount = promo_discount + referral_discount + social_discount
    if total_discount > subtotal:
        total_discount = subtotal
    # track combined in discount_amount; promo_code field keeps promo if any
    tags = []
    if promo_used:
        tags.append(str(promo_used))
    if used_referral:
        tags.append("REFERRAL5")
    if used_social:
        tags.append("SOCIAL2")
    promo_used = "+".join(tags) if tags else None

    total = subtotal - total_discount + delivery_cost
    if total < 0:
        total = Decimal("0")

    if used_referral:
        try:
            user.referral_discount_left = max(0, int(getattr(user, "referral_discount_left", 0) or 0) - 1)
            db.add(user)
        except Exception as e:
            print("[VELORA] referral use:", e)
    if used_social:
        try:
            user.social_discount_left = max(0, int(getattr(user, "social_discount_left", 0) or 0) - 1)
            db.add(user)
        except Exception as e:
            print("[VELORA] social use:", e)

    # Pay with loyalty points (1 point = 1 TJS)
    use_points = bool(getattr(data, "use_points", False))
    points_spent = 0
    if use_points:
        need = int(total.quantize(Decimal("1")))
        have = int(getattr(user, "loyalty_points", 0) or 0)
        if need <= 0:
            raise HTTPException(400, "Нечего оплачивать баллами")
        if have < need:
            raise HTTPException(400, f"Недостаточно баллов. Нужно {need}, у вас {have}")
        points_spent = need
        user.loyalty_points = have - need
        db.add(user)
        if promo_used:
            promo_used = f"{promo_used}+POINTS"
        else:
            promo_used = "POINTS"

    dtype = (data.delivery_type or "home").strip().lower()
    if dtype not in ("home", "office"):
        dtype = "home"
    quote_status = "pickup" if dtype == "office" else "none"

    if use_points:
        is_pickup = dtype == "office"
        order_status = OrderStatus.ready_for_pickup if is_pickup else OrderStatus.paid
        pay_status = PaymentStatus.paid
        if is_pickup:
            quote_status = "pickup"
    else:
        order_status = OrderStatus.awaiting_payment
        pay_status = PaymentStatus.unpaid

    order = Order(
        order_number=generate_order_number(),
        user_id=user.id,
        status=order_status,
        payment_status=pay_status,
        subtotal=subtotal,
        delivery_cost=delivery_cost,
        discount_amount=total_discount,
        promo_code=promo_used,
        total=total,
        delivery_address=delivery_address,
        delivery_city=delivery_city,
        delivery_phone=data.delivery_phone or user.phone,
        delivery_zone_id=zone.id if zone else None,
        payment_method_id=None if use_points else (pm.id if pm else None),
        customer_comment=data.customer_comment,
        delivery_type=dtype,
        delivery_quote_status=quote_status,
        paid_at=datetime.now(timezone.utc) if use_points else None,
        pickup_ready_at=datetime.now(timezone.utc) if (use_points and dtype == "office") else None,
    )
    db.add(order)
    db.flush()

    for d in order_items_data:
        db.add(OrderItem(
            order_id=order.id,
            product_id=d["product"].id,
            variant_id=d["variant"].id if d["variant"] else None,
            product_name=d["product"].name_ru,
            variant_name=d["variant"].name if d["variant"] else None,
            unit_price=d["unit_price"],
            quantity=d["quantity"],
            total_price=d["total_price"],
        ))
        d["product"].stock -= d["quantity"]
        if d["variant"]:
            d["variant"].stock -= d["quantity"]

    if use_points:
        hist_comment = (
            f"Оплачено {points_spent} баллами. "
            + (
                f"Можете забрать в магазине. Срок хранения 3 дня."
                if dtype == "office"
                else "Ожидайте расчёт доставки."
            )
        )
        db.add(OrderStatusHistory(
            order_id=order.id,
            status=order_status,
            comment=hist_comment,
            changed_by_id=user.id,
        ))
        # stats + inviter referral points (purchase > 250 TJS)
        user.total_orders = (user.total_orders or 0) + 1
        user.total_spent = (user.total_spent or 0) + (subtotal or total)
        db.add(user)
        try:
            _award_referral_purchase_point(db, user, subtotal)
        except Exception as e:
            print("[VELORA] referral points:", e)
    else:
        db.add(OrderStatusHistory(
            order_id=order.id,
            status=OrderStatus.awaiting_payment,
            comment="Заказ создан, ожидается оплата",
            changed_by_id=user.id,
        ))

    if data.from_cart:
        cart = get_or_create_cart(db, user)
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

    db.commit()
    db.refresh(order)
    return get_order_detail(order.id, db, user)


def _award_referral_purchase_point(db: Session, buyer: User, subtotal: Decimal) -> None:
    """When referral buys for more than 250 TJS, inviter gets +1 loyalty point."""
    if not buyer or not getattr(buyer, "referred_by", None):
        return
    if float(subtotal or 0) < 250:
        return
    inviter = db.query(User).filter(User.referral_code == buyer.referred_by).first()
    if not inviter:
        return
    inviter.loyalty_points = (inviter.loyalty_points or 0) + 1
    db.add(inviter)


@router.get("", response_model=list[OrderOut])
def list_my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        expire_pickup_orders(db)
    except Exception as e:
        print("[VELORA] expire pickup:", e)

    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    orders = db.query(Order).options(
        joinedload(Order.items),
        joinedload(Order.status_history),
        joinedload(Order.payment_submissions),
    ).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    visible = []
    for o in orders:
        if o.status == OrderStatus.delivered:
            # hide if delivered more than 7 days ago (use updated_at or last history)
            ts = o.updated_at if getattr(o, "updated_at", None) else o.created_at
            # check status history for delivered time
            for h in (o.status_history or []):
                if h.status == OrderStatus.delivered and h.created_at:
                    ts = h.created_at
                    break
            if ts and ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts < cutoff:
                continue
        if o.status == OrderStatus.cancelled:
            ts = o.updated_at if getattr(o, "updated_at", None) else o.created_at
            if ts:
                tsz = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
                if tsz < cutoff:
                    continue
        visible.append(o)
    return [OrderOut.model_validate(o) for o in visible]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_order_detail(order_id, db, user)


def get_order_detail(order_id: int, db: Session, user: User) -> OrderOut:
    order = db.query(Order).options(
        joinedload(Order.items),
        joinedload(Order.status_history),
        joinedload(Order.payment_submissions),
    ).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    if order.user_id != user.id and user.role not in (Role.owner, Role.admin, Role.support):
        raise HTTPException(403, "Нет доступа")
    return OrderOut.model_validate(order)


@router.post("/{order_id}/payment-receipt")
async def upload_payment_receipt(
    order_id: int,
    file: UploadFile = File(...),
    comment: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    if order.payment_status not in (PaymentStatus.unpaid, PaymentStatus.rejected, PaymentStatus.awaiting_review):
        raise HTTPException(400, "Оплата уже обработана")

    allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Только JPEG, PNG, WEBP или PDF")

    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(400, f"Файл слишком большой (макс {settings.MAX_UPLOAD_SIZE_MB} МБ)")

    safe_name = f"{order.order_number}_{uuid.uuid4().hex[:8]}"
    media_url = save_bytes_db(db, content, safe_name, file.content_type)

    submission = PaymentSubmission(
        order_id=order.id,
        user_id=user.id,
        file_path=media_url,
        original_filename=file.filename,
        file_size=len(content),
        mime_type=file.content_type,
        comment=comment,
    )
    db.add(submission)

    order.payment_status = PaymentStatus.awaiting_review
    order.status = OrderStatus.payment_review
    db.add(OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.payment_review,
        comment="Квитанция загружена, ожидает проверки администратора",
        changed_by_id=user.id,
    ))
    db.commit()

    try:
        notify_admin(
            f"🧾 Новый чек\nЗаказ <b>{order.order_number}</b>\nСумма: {order.total} TJS\nКлиент: {user.full_name or user.email}"
        )
    except Exception as e:
        print("[VELORA] receipt notify:", e)
    return {"ok": True, "message": "Квитанция загружена. Ожидайте подтверждения оплаты."}


@router.post("/{order_id}/delivery-response")
def delivery_response(
    order_id: int,
    accept: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Клиент принимает или отклоняет сумму доставки."""
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    if order.delivery_quote_status != "quoted":
        raise HTTPException(400, "Сумма доставки ещё не предложена")

    if accept:
        order.delivery_quote_status = "accepted"
        order.status = OrderStatus.processing  # Упакован
        db.add(OrderStatusHistory(
            order_id=order.id,
            status=OrderStatus.processing,
            comment="Клиент согласился с суммой доставки → упакован",
            changed_by_id=user.id,
        ))
        db.commit()
        return {"ok": True, "message": "Доставка подтверждена. Заказ будет упакован."}
    else:
        order.delivery_quote_status = "rejected"
        order.status = OrderStatus.cancelled
        order.payment_status = PaymentStatus.rejected
        # restock
        for item in order.items:
            from app.models.product import Product
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            if prod:
                prod.stock = (prod.stock or 0) + item.quantity
        db.add(OrderStatusHistory(
            order_id=order.id,
            status=OrderStatus.cancelled,
            comment="Клиент отклонил сумму доставки. Нужен возврат оплаты.",
            changed_by_id=user.id,
        ))
        db.commit()
        return {"ok": True, "message": "Заказ отклонён. Админ вернёт оплату."}


@router.post("/{order_id}/request-delivery")
def request_delivery(
    order_id: int,
    delivery_address: str,
    delivery_zone_id: int | None = None,
    delivery_phone: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Client had pickup, now wants home delivery — admin will quote price."""
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    if order.payment_status != PaymentStatus.paid:
        raise HTTPException(400, "Сначала должна быть подтверждена оплата")
    if (order.delivery_type or "home") != "office" and order.delivery_quote_status != "pickup":
        raise HTTPException(400, "Доставка уже выбрана")
    if order.status in (OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.refunded):
        raise HTTPException(400, "Заказ уже завершён")
    if not delivery_address or not delivery_address.strip():
        raise HTTPException(400, "Укажите адрес")

    order.delivery_type = "home"
    order.delivery_address = delivery_address.strip()
    order.delivery_phone = delivery_phone or order.delivery_phone or user.phone
    order.delivery_quote_status = "none"
    order.delivery_cost = Decimal("0")
    if delivery_zone_id:
        zone = db.query(DeliveryZone).filter(DeliveryZone.id == delivery_zone_id, DeliveryZone.is_active == True).first()
        if zone:
            order.delivery_zone_id = zone.id
            order.delivery_city = zone.city
    order.total = (order.subtotal or 0) - (order.discount_amount or 0)
    db.add(OrderStatusHistory(
        order_id=order.id,
        status=order.status,
        comment="Клиент запросил доставку на дом. Ожидается сумма от админа.",
        changed_by_id=user.id,
    ))
    db.commit()
    try:
        notify_admin(f"🚚 Запрос доставки\nЗаказ <b>{order.order_number}</b>\nАдрес: {order.delivery_address}")
    except Exception:
        pass
    return get_order_detail(order.id, db, user)


def expire_pickup_orders(db: Session) -> int:
    """After 3 days at store without pickup → refund + restock."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    q = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(
            Order.delivery_type == "office",
            Order.status == OrderStatus.ready_for_pickup,
            Order.payment_status == PaymentStatus.paid,
            Order.pickup_ready_at != None,
            Order.pickup_ready_at < cutoff,
        )
    )
    n = 0
    for order in q.all():
        order.status = OrderStatus.refunded
        order.payment_status = PaymentStatus.refunded
        for it in order.items or []:
            if it.product_id:
                prod = db.query(Product).filter(Product.id == it.product_id).first()
                if prod:
                    prod.stock = (prod.stock or 0) + (it.quantity or 0)
                    if not prod.is_published:
                        prod.is_published = True
        db.add(OrderStatusHistory(
            order_id=order.id,
            status=OrderStatus.refunded,
            comment="Срок хранения в магазине (3 дня) истёк. Оплата возвращается, товар снова в каталоге.",
            changed_by_id=None,
        ))
        n += 1
        try:
            notify_admin(f"↩️ Истёк срок хранения\nЗаказ <b>{order.order_number}</b> — возврат")
        except Exception:
            pass
    if n:
        db.commit()
    return n
