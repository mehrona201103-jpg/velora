from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import aiofiles

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.services.media_store import save_bytes_db
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserLogin, UserOut, Token, UserUpdate, VerificationSubmit
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])



def ensure_referral_code(db: Session, user: User) -> User:
    if not getattr(user, "referral_code", None):
        import uuid as _uuid
        user.referral_code = _uuid.uuid4().hex[:8].upper()
        db.commit()
        db.refresh(user)
    return user


@router.post("/register", response_model=Token)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if not data.email and not data.phone:
        raise HTTPException(400, "Email или телефон обязателен")
    if data.device_type not in ("phone", "tablet", "pc"):
        raise HTTPException(400, "Выберите устройство: phone, tablet или pc")
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email уже зарегистрирован")
    if data.phone and db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(400, "Телефон уже зарегистрирован")

    my_code = uuid.uuid4().hex[:8].upper()
    referred = None
    if getattr(data, "referral_code", None):
        ref = (data.referral_code or "").strip().upper()
        if ref:
            inv = db.query(User).filter(User.referral_code == ref).first()
            if not inv:
                raise HTTPException(400, "Реферальный код не найден")
            referred = ref
    user = User(
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=Role.customer,
        device_type=data.device_type,
        referral_code=my_code,
        referred_by=referred,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        print("[VELORA] register error:", e)
        raise HTTPException(400, "Не удалось создать аккаунт. Email или телефон уже заняты, либо ошибка сервера.")

    if referred:
        try:
            inviter = db.query(User).filter(User.referral_code == referred).first()
            if inviter and inviter.id != user.id:
                # Both get one 5% discount on a purchase
                inviter.referral_discount_left = (getattr(inviter, "referral_discount_left", 0) or 0) + 1
                user.referral_discount_left = (getattr(user, "referral_discount_left", 0) or 0) + 1
                inviter.loyalty_points = (inviter.loyalty_points or 0) + 10
                user.loyalty_points = (user.loyalty_points or 0) + 5
                db.commit()
                db.refresh(user)
            elif not inviter:
                # invalid code — clear referred_by
                user.referred_by = None
                db.commit()
        except Exception as e:
            print("[VELORA] referral bonus skip:", e)

    token = create_access_token(user.id)
    try:
        user_out = UserOut.model_validate(user)
    except Exception:
        # fallback minimal
        user_out = UserOut(
            id=user.id,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            is_active=bool(user.is_active),
            language=getattr(user, "language", "ru") or "ru",
            device_type=getattr(user, "device_type", "phone") or "phone",
            created_at=user.created_at,
        )
    return Token(access_token=token, user=user_out)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.email == data.login) | (User.phone == data.login)
    ).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(400, "Аккаунт заблокирован")

    user = ensure_referral_code(db, user)
    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ensure_referral_code(db, user)



@router.post("/heartbeat")
def heartbeat(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Ping that user is active in the app — updates last activity for online counter."""
    from datetime import datetime, timezone
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    return {"ok": True}

@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = data.model_dump(exclude_unset=True)
    old_tg = getattr(user, "telegram_chat_id", None)
    for k, v in payload.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    # notify bot when chat id linked/changed
    new_tg = getattr(user, "telegram_chat_id", None)
    if new_tg and new_tg != old_tg:
        try:
            from app.services.telegram import send_telegram_sync
            send_telegram_sync(
                new_tg,
                "✅ <b>Ваш аккаунт VELORA привязан.</b>\n\n"
                "Теперь вы будете получать уведомления о статусе заказов.\n"
                "Бот: @velorashoping_bot",
            )
        except Exception as e:
            print("[VELORA] tg link notify:", e)
    return user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Только JPEG/PNG/WEBP")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "Макс. 5 МБ")
    name = f"u{user.id}_{uuid.uuid4().hex[:8]}.jpg"
    user.avatar_url = save_bytes_db(db, content, name, file.content_type)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/verification")
async def submit_verification(
    full_name: str = Form(...),
    age_confirmed: bool = Form(True),
    passport_selfie: UploadFile = File(...),
    passport_front: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not age_confirmed:
        raise HTTPException(400, "Необходимо подтвердить возраст 18+")
    if user.verification_status == "approved":
        raise HTTPException(400, "Уже подтверждён")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    for f in (passport_selfie, passport_front):
        if f.content_type not in allowed:
            raise HTTPException(400, "Только изображения")

    # files stored in DB

    async def save(up: UploadFile, prefix: str) -> str:
        content = await up.read()
        if len(content) > 8 * 1024 * 1024:
            raise HTTPException(400, "Файл слишком большой")
        name = f"u{user.id}_{prefix}_{uuid.uuid4().hex[:8]}.jpg"
        return save_bytes_db(db, content, name, up.content_type)

    user.verification_full_name = full_name
    user.verification_age_confirmed = True
    user.verification_passport_selfie = await save(passport_selfie, "selfie")
    user.verification_passport_front = await save(passport_front, "front")
    user.verification_status = "pending"
    user.verification_reject_reason = None
    db.commit()
    return {"ok": True, "message": "Заявка на идентификацию отправлена. Ожидайте проверки."}


@router.post("/me/welcome-seen")
def mark_welcome_seen(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Close welcome modal without claiming bonus."""
    user.welcome_seen = True
    db.add(user)
    db.commit()
    return {"ok": True, "welcome_seen": True}


@router.post("/me/claim-social-bonus")
def claim_social_bonus(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Client says they subscribed — grant 2% on first purchase (one time)."""
    user.welcome_seen = True
    if int(getattr(user, "social_discount_left", 0) or 0) <= 0 and int(getattr(user, "total_orders", 0) or 0) == 0:
        user.social_discount_left = 1
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "ok": True,
        "welcome_seen": True,
        "social_discount_left": int(user.social_discount_left or 0),
        "message": "Скидка 2% на первую покупку активирована",
    }


from pydantic import BaseModel
from typing import Optional as Opt


class PushSubIn(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: Opt[str] = None


@router.get("/push/vapid-public-key")
def vapid_public_key(db: Session = Depends(get_db)):
    from app.services.push import get_vapid_public_key
    key = get_vapid_public_key(db)
    return {"publicKey": key or ""}


@router.get("/push/status")
def push_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.models.push import PushSubscription
    try:
        PushSubscription.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    n = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).count()
    return {"devices": n, "ok": n > 0}


@router.post("/push/subscribe")
def push_subscribe(
    data: PushSubIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.push import PushSubscription
    from app.services.push import notify_user_push
    PushSubscription.__table__.create(bind=db.get_bind(), checkfirst=True)
    if not data.endpoint or not data.p256dh or not data.auth:
        raise HTTPException(400, "Неполные данные подписки")
    row = db.query(PushSubscription).filter(PushSubscription.endpoint == data.endpoint).first()
    if row:
        row.user_id = user.id
        row.p256dh = data.p256dh
        row.auth = data.auth
        row.user_agent = data.user_agent
    else:
        db.add(PushSubscription(
            user_id=user.id,
            endpoint=data.endpoint,
            p256dh=data.p256dh,
            auth=data.auth,
            user_agent=data.user_agent,
        ))
    db.commit()
    n = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).count()
    print(f"[VELORA] push subscribed user={user.id} devices={n}")
    result = notify_user_push(
        db, user.id,
        "VELORA",
        "Уведомления подключены. Статусы заказов будут приходить сюда.",
        url="/orders",
    )
    return {
        "ok": True,
        "devices": n,
        "test_sent": int(result.get("sent") or 0),
        "test_errors": result.get("errors") or [],
    }


@router.post("/push/test")
def push_test(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Send a test notification to current user's devices."""
    from app.models.push import PushSubscription
    from app.services.push import notify_user_push
    try:
        PushSubscription.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    n = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).count()
    if n == 0:
        raise HTTPException(
            400,
            "Подписка не найдена на сервере. Нажмите «Включить уведомления».",
        )
    result = notify_user_push(
        db,
        user.id,
        "VELORA — тест",
        "Уведомления работают! Вы будете получать статусы заказов.",
        url="/orders",
    )
    sent = int(result.get("sent") or 0)
    if sent == 0:
        errors = result.get("errors") or []
        err_text = (errors[0] if errors else "отправка не удалась")
        raise HTTPException(
            400,
            "Не удалось доставить на телефон. Нажмите «Включить уведомления» ещё раз "
            "(обновится ключ подписки). "
            f"Причина: {str(err_text)[:140]}",
        )
    return {"ok": True, "sent": sent, "total": result.get("total", n)}


@router.post("/push/reset-keys")
def push_reset_keys(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role not in ("owner", "admin"):
        raise HTTPException(403, "Только админ")
    from app.services.push import reset_vapid_keys
    from app.models.push import PushSubscription
    pub, _, _ = reset_vapid_keys(db)
    try:
        db.query(PushSubscription).delete()
        db.commit()
    except Exception:
        db.rollback()
    return {"ok": True, "publicKey": pub, "message": "Ключи сброшены. Всем нужно снова включить уведомления."}


@router.delete("/push/subscribe")
def push_unsubscribe(
    data: PushSubIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.push import PushSubscription
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == data.endpoint,
        PushSubscription.user_id == user.id,
    ).delete()
    db.commit()
    return {"ok": True}
