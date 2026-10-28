from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import uuid
import aiofiles

from app.core.database import get_db
from app.core.config import settings
from app.services.media_store import save_bytes_db
from app.services.telegram import notify_admin, notify_user_telegram, status_ru
from app.models.user import User, Role
from app.models.order import Order, OrderStatusHistory, OrderStatus, PaymentStatus
from app.models.payment import PaymentMethod, PaymentSubmission
from app.models.delivery import DeliveryZone
from app.models.product import Category, Product, ProductImage, ProductVariant
from app.models.settings import AppSetting, AdminAuditLog
from app.schemas.order import OrderOut, PaymentMethodOut, DeliveryZoneOut
from app.schemas.product import CategoryOut, ProductOut
from app.api.deps import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


class PaymentMethodCreate(BaseModel):
    code: str
    name: str
    recipient_name: str
    account_number: Optional[str] = None
    instructions: Optional[str] = None
    tg_username: Optional[str] = None
    tg_deep_link: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class DeliveryZoneCreate(BaseModel):
    name: str
    city: str
    district: Optional[str] = None
    description: Optional[str] = None
    base_price: Decimal = 0
    free_from_amount: Optional[Decimal] = None
    estimated_days_min: int = 1
    estimated_days_max: int = 3
    is_active: bool = True
    delivery_type: str = "home"
    instructions: Optional[str] = None


class StatusUpdate(BaseModel):
    status: OrderStatus
    comment: Optional[str] = None


class PaymentReview(BaseModel):
    approve: bool
    reason: Optional[str] = None


class CategoryCreate(BaseModel):
    name_ru: str
    name_tj: Optional[str] = None
    name_en: Optional[str] = None
    slug: str
    is_active: bool = True
    sort_order: int = 0


class ProductAdminCreate(BaseModel):
    sku: str
    name_ru: str
    name_tj: Optional[str] = None
    name_en: Optional[str] = None
    description_ru: Optional[str] = None
    category_id: Optional[int] = None
    purchase_price: Decimal = 0
    price: Decimal
    discount_percent: int = 0
    stock: int = 0
    is_published: bool = True
    delivery_days_min: int = 14
    delivery_days_max: int = 30
    image_urls: List[str] = []
    variants: List[dict] = []  # [{name, stock, price_modifier}]


class SettingUpdate(BaseModel):
    key: str
    value: str


class VerificationReview(BaseModel):
    approve: bool
    reason: Optional[str] = None


def log_action(db: Session, user: User, action: str, entity_type: str = None, entity_id: int = None, details: str = None):
    db.add(AdminAuditLog(user_id=user.id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


def get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.query(AppSetting).filter(AppSetting.key == key).first()
    return s.value if s and s.value else default


@router.get("/orders", response_model=List[OrderOut])
def admin_list_orders(
    status: Optional[OrderStatus] = None,
    payment_status: Optional[PaymentStatus] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner, Role.support)),
):
    query = db.query(Order).options(joinedload(Order.items), joinedload(Order.status_history), joinedload(Order.payment_submissions))
    if status:
        query = query.filter(Order.status == status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    orders = query.order_by(Order.created_at.desc()).limit(500).all()
    search = (q or "").strip().upper()
    visible = []
    for o in orders:
        if search:
            blob = f"{o.order_number} {o.delivery_address or ''} {o.delivery_city or ''} {o.id}"
            for it in (o.items or []):
                blob += f" {it.product_name or ''} {getattr(it, 'product_id', '')}"
            if search not in blob.upper() and search not in str(o.id):
                continue
            visible.append(o)
            continue
        # default list: hide delivered/cancelled/refunded
        if o.status in (OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.refunded):
            continue
        visible.append(o)
    return [OrderOut.model_validate(o) for o in visible]


@router.get("/orders/{order_id}/receipts")
def list_receipts(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    subs = db.query(PaymentSubmission).filter(PaymentSubmission.order_id == order_id).order_by(PaymentSubmission.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "file_path": s.file_path,
            "url": f"/api/v1/admin/receipts/{s.id}",
            "original_filename": s.original_filename,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "is_reviewed": s.is_reviewed,
            "comment": s.comment,
        }
        for s in subs
    ]


@router.get("/receipts/{submission_id}")
def get_receipt_file(submission_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    from fastapi.responses import Response
    from app.models.media import MediaBlob
    sub = db.query(PaymentSubmission).filter(PaymentSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "Не найдено")
    fp = sub.file_path or ""
    # DB media: /api/v1/media/123
    if "/api/v1/media/" in fp:
        try:
            mid = int(fp.rstrip("/").split("/")[-1])
        except ValueError:
            raise HTTPException(404, "Файл не найден")
        blob = db.query(MediaBlob).filter(MediaBlob.id == mid).first()
        if not blob:
            raise HTTPException(404, "Файл не найден")
        return Response(content=blob.data, media_type=sub.mime_type or blob.content_type or "image/jpeg")
    path = Path(fp)
    if not path.is_file():
        path = Path(settings.UPLOAD_DIR) / "receipts" / path.name
    if not path.is_file():
        raise HTTPException(404, "Файл не найден (старый файл мог пропасть после деплоя)")
    return FileResponse(path, filename=sub.original_filename or path.name)


@router.post("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    prev = order.status
    order.status = data.status
    if data.status == OrderStatus.cancelled and prev != OrderStatus.cancelled:
        from app.models.product import Product
        for item in order.items:
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            if prod:
                prod.stock = (prod.stock or 0) + item.quantity
        order.payment_status = PaymentStatus.rejected
        order.delivery_quote_status = "rejected"
    db.add(OrderStatusHistory(
        order_id=order.id,
        status=data.status,
        comment=data.comment or f"Статус: {data.status.value}",
        changed_by_id=user.id,
    ))
    log_action(db, user, "order_status_update", "order", order.id, data.status.value)
    db.commit()
    try:
        cust = db.query(User).filter(User.id == order.user_id).first()
        if cust and getattr(cust, "telegram_chat_id", None):
            notify_user_telegram(
                cust.telegram_chat_id,
                f"📦 <b>VELORA</b>\nЗаказ <code>{order.order_number}</code>\nСтатус: <b>{status_ru(data.status)}</b>",
            )
    except Exception as e:
        print("[VELORA] status notify:", e)
    return {"ok": True}


@router.post("/orders/{order_id}/review-payment")
def review_payment(
    order_id: int,
    data: PaymentReview,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    if order.payment_status != PaymentStatus.awaiting_review:
        raise HTTPException(400, "Заказ не ожидает проверки оплаты")

    submission = db.query(PaymentSubmission).filter(
        PaymentSubmission.order_id == order.id,
        PaymentSubmission.is_reviewed == False,
    ).order_by(PaymentSubmission.created_at.desc()).first()

    tg_channel = get_setting(db, "telegram_channel_url", "https://t.me/")

    if data.approve:
        order.payment_status = PaymentStatus.paid
        order.status = OrderStatus.paid
        order.paid_at = datetime.now(timezone.utc)
        comment = (
            f"Оплата подтверждена. Ожидайте товар — мы сообщим о приходе в нашем Telegram-канале: {tg_channel}"
        )
        # update user stats
        u = db.query(User).filter(User.id == order.user_id).first()
        if u:
            u.total_orders = (u.total_orders or 0) + 1
            u.total_spent = (u.total_spent or 0) + order.total
    else:
        order.payment_status = PaymentStatus.rejected
        order.status = OrderStatus.awaiting_payment
        order.payment_rejection_reason = data.reason or "Отклонено администратором"
        comment = f"Оплата отклонена: {order.payment_rejection_reason}"

    if submission:
        submission.is_reviewed = True
        submission.reviewed_by_id = user.id
        submission.review_comment = comment
        submission.reviewed_at = datetime.now(timezone.utc)

    db.add(OrderStatusHistory(
        order_id=order.id,
        status=order.status,
        comment=comment,
        changed_by_id=user.id,
    ))
    log_action(db, user, "payment_review", "order", order.id, "approved" if data.approve else "rejected")
    db.commit()
    try:
        cust = db.query(User).filter(User.id == order.user_id).first()
        if data.approve:
            notify_admin(f"✅ Оплата подтверждена\nЗаказ <b>{order.order_number}</b>\nСумма: {order.total} TJS")
            if cust and getattr(cust, "telegram_chat_id", None):
                notify_user_telegram(
                    cust.telegram_chat_id,
                    f"✅ <b>VELORA</b>: оплата по заказу {order.order_number} подтверждена. Ожидайте расчёт доставки."
                )
            if cust:
                pts = int(float(order.subtotal or 0) // 100)
                if pts > 0:
                    cust.loyalty_points = (cust.loyalty_points or 0) + pts
                    db.commit()
        else:
            notify_admin(f"❌ Оплата отклонена\n{order.order_number}")
            if cust and getattr(cust, "telegram_chat_id", None):
                notify_user_telegram(
                    cust.telegram_chat_id,
                    f"❌ <b>VELORA</b>: оплата по заказу {order.order_number} отклонена. {data.reason or ''}"
                )
    except Exception as e:
        print("[VELORA] notify:", e)
    return {
        "ok": True,
        "payment_status": order.payment_status,
        "status": order.status,
        "message": comment,
        "telegram_channel": tg_channel if data.approve else None,
    }


@router.get("/payment-methods")
def admin_payment_methods(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    return db.query(PaymentMethod).order_by(PaymentMethod.sort_order).all()


@router.post("/payment-methods")
def create_payment_method(data: PaymentMethodCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    pm = PaymentMethod(**data.model_dump())
    db.add(pm)
    log_action(db, user, "create_payment_method", details=data.name)
    db.commit()
    db.refresh(pm)
    return pm


class PaymentMethodUpdate(BaseModel):
    name: Optional[str] = None
    recipient_name: Optional[str] = None
    account_number: Optional[str] = None
    instructions: Optional[str] = None
    tg_username: Optional[str] = None
    tg_deep_link: Optional[str] = None
    is_active: Optional[bool] = None
    stars_per_usd: Optional[float] = None


@router.patch("/payment-methods/{pm_id}")
def update_payment_method(pm_id: int, data: PaymentMethodUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    pm = db.query(PaymentMethod).filter(PaymentMethod.id == pm_id).first()
    if not pm:
        raise HTTPException(404)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(pm, k, v)
    db.commit()
    db.refresh(pm)
    return pm


@router.get("/delivery-zones")
def admin_delivery_zones(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    return db.query(DeliveryZone).all()


@router.post("/delivery-zones")
def create_delivery_zone(data: DeliveryZoneCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    zone = DeliveryZone(**data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.patch("/delivery-zones/{zone_id}")
def update_delivery_zone(zone_id: int, data: DeliveryZoneCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    zone = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(zone, k, v)
    db.commit()
    db.refresh(zone)
    return zone


@router.post("/categories")
def create_category(data: CategoryCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    if db.query(Category).filter(Category.slug == data.slug).first():
        raise HTTPException(400, "Slug уже есть")
    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.post("/products")
def admin_create_product(data: ProductAdminCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    if db.query(Product).filter(Product.sku == data.sku).first():
        raise HTTPException(400, "SKU уже существует")
    product = Product(
        sku=data.sku,
        name_ru=data.name_ru,
        name_tj=data.name_tj,
        name_en=data.name_en,
        description_ru=data.description_ru,
        category_id=data.category_id,
        purchase_price=data.purchase_price,
        price=data.price,
        discount_percent=data.discount_percent,
        stock=data.stock,
        is_published=data.is_published,
        delivery_days_min=data.delivery_days_min,
        delivery_days_max=data.delivery_days_max,
    )
    db.add(product)
    db.flush()
    for i, url in enumerate(data.image_urls[:10]):
        db.add(ProductImage(product_id=product.id, url=url, is_main=(i == 0), sort_order=i))
    for v in data.variants:
        db.add(ProductVariant(
            product_id=product.id,
            name=v.get("name", "Вариант"),
            stock=int(v.get("stock", 0)),
            price_modifier=Decimal(str(v.get("price_modifier", 0))),
            is_active=True,
        ))
    db.commit()
    db.refresh(product)
    return {"id": product.id, "sku": product.sku, "name_ru": product.name_ru}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    rows = db.query(AppSetting).all()
    return {r.key: r.value for r in rows}


@router.post("/settings")
def set_setting(data: SettingUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    row = db.query(AppSetting).filter(AppSetting.key == data.key).first()
    if row:
        row.value = data.value
    else:
        db.add(AppSetting(key=data.key, value=data.value))
    log_action(db, user, "update_setting", details=data.key)
    db.commit()
    return {"ok": True}


@router.get("/verifications")
def list_verifications(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    users = db.query(User).filter(User.verification_status == "pending").order_by(User.updated_at.desc()).all()
    return [
        {
            "id": u.id,
            "full_name": u.verification_full_name or u.full_name,
            "email": u.email,
            "phone": u.phone,
            "passport_selfie": u.verification_passport_selfie,
            "passport_front": u.verification_passport_front,
            "created_at": u.updated_at.isoformat() if u.updated_at else None,
        }
        for u in users
    ]


@router.post("/verifications/{user_id}")
def review_verification(
    user_id: int,
    data: VerificationReview,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404)
    if data.approve:
        target.verification_status = "approved"
        target.is_verified = True
        target.verification_reject_reason = None
    else:
        target.verification_status = "rejected"
        target.is_verified = False
        target.verification_reject_reason = data.reason or "Отклонено"
    log_action(db, user, "verification_review", "user", target.id, "approved" if data.approve else "rejected")
    db.commit()
    return {"ok": True}




class ProductAdminUpdate(BaseModel):
    name_ru: Optional[str] = None
    description_ru: Optional[str] = None
    price: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    stock: Optional[int] = None
    is_published: Optional[bool] = None


@router.patch("/products/{product_id}")
def update_product(
    product_id: int,
    data: ProductAdminUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Товар не найден")
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return {"ok": True, "id": product.id, "discount_percent": product.discount_percent, "is_published": product.is_published}

@router.post("/products/{product_id}/images")
async def upload_product_images(
    product_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Товар не найден")
    existing = db.query(ProductImage).filter(ProductImage.product_id == product_id).count()
    if existing + len(files) > 10:
        raise HTTPException(400, "Максимум 10 фото на товар")
    allowed = {"image/jpeg", "image/png", "image/webp"}
    urls = []
    for i, f in enumerate(files):
        if f.content_type not in allowed:
            raise HTTPException(400, f"Неверный тип файла: {f.filename}")
        content = await f.read()
        if len(content) > 8 * 1024 * 1024:
            raise HTTPException(400, "Файл слишком большой")
        name = f"p{product_id}_{uuid.uuid4().hex[:8]}.jpg"
        url = save_bytes_db(db, content, name, f.content_type)
        db.add(ProductImage(
            product_id=product_id,
            url=url,
            is_main=(existing == 0 and i == 0),
            sort_order=existing + i,
        ))
        urls.append(url)
    db.commit()
    return {"ok": True, "urls": urls}



class DeliveryQuoteIn(BaseModel):
    amount: Decimal
    comment: Optional[str] = None


@router.post("/orders/{order_id}/delivery-quote")
def set_delivery_quote(
    order_id: int,
    data: DeliveryQuoteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, detail="Заказ не найден")
    amount = Decimal(str(data.amount))
    if amount < 0:
        raise HTTPException(400, detail="Сумма не может быть отрицательной")
    subtotal = Decimal(str(order.subtotal or 0))
    order.delivery_cost = amount
    order.total = subtotal + amount
    try:
        order.delivery_quote_status = "quoted"
    except Exception:
        pass
    note = (
        f"Стоимость доставки: {amount} TJS. "
        "Сумма может измениться до прихода товара — мы отправим её ещё раз, когда товар будет на складе."
    )
    # allow re-quote even if previously accepted (warehouse re-check)
    try:
        order.delivery_quote_status = "quoted"
    except Exception:
        pass
    if data.comment:
        order.delivery_notes = data.comment
        note = data.comment
    else:
        order.delivery_notes = note
    db.add(OrderStatusHistory(
        order_id=order.id,
        status=order.status,
        comment=note,
        changed_by_id=user.id,
    ))
    db.commit()
    db.refresh(order)
    log_action(db, user, "delivery_quote", "order", order.id, str(amount))
    try:
        cust = db.query(User).filter(User.id == order.user_id).first()
        if cust and getattr(cust, "telegram_chat_id", None):
            notify_user_telegram(
                cust.telegram_chat_id,
                f"🚚 <b>VELORA</b> заказ {order.order_number}: доставка <b>{amount} TJS</b>. Откройте заказ и нажмите «Согласен» или «Отказ»."
            )
        notify_admin(f"🚚 Доставка {amount} TJS выставлена по {order.order_number}")
    except Exception as e:
        print("[VELORA] quote notify:", e)
    return {
        "ok": True,
        "delivery_cost": float(order.delivery_cost),
        "total": float(order.total),
        "message": f"Клиенту отправлена сумма доставки {amount} TJS",
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    rows = db.query(User).order_by(User.created_at.desc()).limit(200).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "phone": u.phone,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_active": u.is_active,
            "verification_status": getattr(u, "verification_status", None),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "device_type": getattr(u, "device_type", None),
        }
        for u in rows
    ]


from fastapi import File, UploadFile
from app.services.media_store import save_bytes_db
import json

@router.post("/banners/upload")
async def upload_banners(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    """Upload up to 5 images/videos for home banner carousel."""
    files = files[:5]
    slides = []
    for f in files:
        content = await f.read()
        if len(content) > 40 * 1024 * 1024:
            continue
        ct = f.content_type or "application/octet-stream"
        url = save_bytes_db(db, content, f.filename or "banner.bin", ct)
        typ = "video" if ct.startswith("video") else "image"
        slides.append({"type": typ, "url": url, "title": "VELORA", "subtitle": ""})
    # merge with existing or replace
    row = db.query(AppSetting).filter(AppSetting.key == "home_banners").first()
    payload = json.dumps(slides, ensure_ascii=False)
    if row:
        row.value = payload
    else:
        db.add(AppSetting(key="home_banners", value=payload))
    db.commit()
    return {"ok": True, "count": len(slides), "banners": slides}


from datetime import datetime, timezone
import json

@router.post("/broadcast")
def send_broadcast(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    """Push a short message shown as modal to clients (polled)."""
    text = (data.get("text") or "").strip()
    if not text or len(text) > 500:
        raise HTTPException(400, "Текст 1–500 символов")
    payload = json.dumps({
        "id": datetime.now(timezone.utc).timestamp(),
        "text": text,
        "at": datetime.now(timezone.utc).isoformat(),
        "by": user.full_name or user.email or "admin",
    }, ensure_ascii=False)
    row = db.query(AppSetting).filter(AppSetting.key == "live_broadcast").first()
    if row:
        row.value = payload
    else:
        db.add(AppSetting(key="live_broadcast", value=payload))
    db.commit()
    log_action(db, user, "broadcast", details=text[:80])
    return {"ok": True, "message": "Рассылка отправлена"}
