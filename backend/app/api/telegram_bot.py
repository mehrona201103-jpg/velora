"""Telegram bot webhook: Russian + inline buttons. Always returns ok to Telegram."""
import re
import traceback
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, Role
from app.models.order import Order
from app.models.product import Product
from app.services.telegram import (
    send_telegram_sync,
    answer_callback,
    main_menu_keyboard,
    status_ru,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])

HELP = (
    "👋 <b>VELORA Support</b>\n\n"
    "Выберите действие кнопкой или отправьте номер заказа:\n"
    "<code>VL-20261027-XXXXXX</code>\n\n"
    "Сайт: https://velora-tj.up.railway.app"
)


def _role_val(user: User) -> str:
    r = getattr(user, "role", None)
    return r.value if hasattr(r, "value") else str(r or "")


def _link_user(db: Session, chat_id: int, payload: str = "") -> User | None:
    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if user:
        return user
    if payload.isdigit():
        user = db.query(User).filter(User.id == int(payload)).first()
        if user:
            user.telegram_chat_id = str(chat_id)
            db.commit()
            return user
    return None


def _track(db: Session, code: str, chat_id: int) -> str:
    code = code.strip().upper()
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.status_history))
        .filter(Order.order_number == code)
        .first()
    )
    if not order:
        return f"❌ Заказ <code>{code}</code> не найден.\nПример: VL-20261027-2C49CF"
    linked = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if linked and _role_val(linked) not in ("owner", "admin") and order.user_id != linked.id:
        return "🔒 Этот заказ принадлежит другому аккаунту."
    items = ", ".join((i.product_name or "?") for i in (order.items or [])[:5]) or "—"
    hist = ""
    for h in (order.status_history or [])[-6:]:
        hist += f"\n· {status_ru(h.status)}"
    return (
        f"📦 <b>Заказ {order.order_number}</b>\n"
        f"Статус: <b>{status_ru(order.status)}</b>\n"
        f"Сумма: <b>{order.total}</b> TJS\n"
        f"Товары: {items}\n"
        f"Город: {order.delivery_city or '—'}"
        + (f"\n\nИстория:{hist}" if hist else "")
    )


def _search(db: Session, q: str) -> str:
    q = (q or "").strip()
    if len(q) < 2:
        return "Напишите название товара (от 2 букв), например: наушники"
    rows = (
        db.query(Product)
        .filter(Product.is_published == True, Product.name_ru.ilike(f"%{q}%"))
        .order_by(Product.id.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return f"Ничего не найдено по «{q}»"
    lines = [f"🔎 Найдено по «{q}»:"]
    for p in rows:
        price = p.final_price if hasattr(p, "final_price") else p.price
        lines.append(f"• <b>{p.name_ru}</b> — {price} TJS\n  https://velora-tj.up.railway.app/product/{p.id}")
    return "\n".join(lines)


def _my_orders(db: Session, chat_id: int) -> str:
    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if not user:
        return (
            "Аккаунт ещё не привязан.\n"
            f"Ваш Chat ID: <code>{chat_id}</code>\n"
            "Скопируйте его в Профиль → Telegram на сайте, затем снова /start"
        )
    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(8)
        .all()
    )
    if not orders:
        return "У вас пока нет заказов."
    lines = ["📋 <b>Ваши заказы</b>:"]
    for o in orders:
        lines.append(f"• <code>{o.order_number}</code> — {status_ru(o.status)} — {o.total} TJS")
    return "\n".join(lines)


def _handle_text(db: Session, chat_id: int, text: str) -> None:
    low = (text or "").lower().strip()
    kb = main_menu_keyboard()

    if low.startswith("/start") or low in ("start", "старт"):
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        user = _link_user(db, chat_id, payload)
        if user:
            send_telegram_sync(
                chat_id,
                f"✅ <b>Аккаунт VELORA привязан.</b>\nВы будете получать статусы заказов.\n\nChat ID: <code>{chat_id}</code>",
                reply_markup=kb,
            )
        else:
            send_telegram_sync(
                chat_id,
                "👋 <b>VELORA</b>\n\n"
                f"Ваш Telegram ID: <code>{chat_id}</code>\n\n"
                "1) Скопируйте ID\n"
                "2) Откройте приложение → Профиль → Telegram\n"
                "3) Вставьте ID и нажмите «Сохранить»\n\n"
                "После сохранения придёт подтверждение о привязке.",
                reply_markup=kb,
            )
        return

    if low.startswith("/help") or low in ("помощь", "меню", "menu", "help"):
        send_telegram_sync(chat_id, HELP, reply_markup=kb)
        return

    if low.startswith("/track"):
        parts = text.split(maxsplit=1)
        code = parts[1].strip() if len(parts) > 1 else ""
        if code:
            send_telegram_sync(chat_id, _track(db, code, chat_id), reply_markup=kb)
        else:
            send_telegram_sync(chat_id, "Отправьте: /track VL-… или просто номер заказа", reply_markup=kb)
        return

    if low.startswith("/search"):
        parts = text.split(maxsplit=1)
        q = parts[1] if len(parts) > 1 else ""
        send_telegram_sync(chat_id, _search(db, q), reply_markup=kb)
        return

    if low.startswith("/orders") or low in ("заказы", "мои заказы"):
        send_telegram_sync(chat_id, _my_orders(db, chat_id), reply_markup=kb)
        return

    m = re.search(r"\b(VL-[A-Z0-9\-]+)\b", text.upper())
    if m:
        send_telegram_sync(chat_id, _track(db, m.group(1), chat_id), reply_markup=kb)
        return

    if text and not text.startswith("/"):
        send_telegram_sync(chat_id, _search(db, text), reply_markup=kb)
        return

    send_telegram_sync(chat_id, HELP, reply_markup=kb)


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        print("[VELORA] tg update keys:", list(body.keys()))

        cq = body.get("callback_query")
        if cq:
            chat_id = ((cq.get("message") or {}).get("chat") or {}).get("id")
            data = (cq.get("data") or "").strip()
            answer_callback(cq.get("id") or "", "")
            if chat_id:
                kb = main_menu_keyboard()
                if data == "menu:help":
                    send_telegram_sync(chat_id, HELP, reply_markup=kb)
                elif data == "menu:orders":
                    send_telegram_sync(chat_id, _my_orders(db, chat_id), reply_markup=kb)
                elif data == "menu:track":
                    send_telegram_sync(
                        chat_id,
                        "🔍 Пришлите номер заказа:\n<code>VL-20261027-XXXXXX</code>",
                        reply_markup=kb,
                    )
                elif data == "menu:search":
                    send_telegram_sync(
                        chat_id,
                        "🛍 Напишите название товара в чат",
                        reply_markup=kb,
                    )
                else:
                    send_telegram_sync(chat_id, HELP, reply_markup=kb)
            return {"ok": True}

        msg = body.get("message") or body.get("edited_message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        text = (msg.get("text") or "").strip()
        if chat_id and text:
            _handle_text(db, int(chat_id), text)
        elif chat_id:
            send_telegram_sync(chat_id, HELP, reply_markup=main_menu_keyboard())
    except Exception:
        print("[VELORA] webhook error:\n", traceback.format_exc())
    return {"ok": True}


@router.get("/webhook-info")
def webhook_info():
    """Check Telegram webhook status (for debugging)."""
    import httpx
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
            return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/setup-webhook")
def setup_webhook():
    """Force set webhook to PUBLIC_BASE_URL/api/v1/telegram/webhook"""
    import httpx
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    base = (getattr(settings, "PUBLIC_BASE_URL", None) or "https://velora-tj.up.railway.app").rstrip("/")
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN empty"}
    url = f"{base}/api/v1/telegram/webhook"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": url, "allowed_updates": ["message", "callback_query", "edited_message"]},
            )
            return {"set": r.json(), "webhook_url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/link-info")
def link_info():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    return {"configured": bool(token)}
