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
            referred = ref
            # bonus to referrer later on first paid order — store code only
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
            if inviter:
                inviter.loyalty_points = (inviter.loyalty_points or 0) + 10
                user.loyalty_points = (user.loyalty_points or 0) + 5
                db.commit()
                db.refresh(user)
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
