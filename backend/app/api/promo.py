from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.promo import PromoCode
from app.models.user import User, Role
from app.api.deps import require_roles, get_current_user_optional

router = APIRouter(prefix="/promo", tags=["promo"])


class PromoIn(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    discount_percent: int = 0
    discount_fixed: float = 0
    max_uses: int = 0
    min_order_tjs: float = 0
    note: Optional[str] = None
    is_active: bool = True


class PromoCheck(BaseModel):
    code: str
    subtotal: float = 0


@router.get("/admin/list")
def admin_list(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    PromoCode.__table__.create(bind=db.get_bind(), checkfirst=True)
    return db.query(PromoCode).order_by(PromoCode.id.desc()).all()


@router.post("/admin")
def admin_create(data: PromoIn, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    PromoCode.__table__.create(bind=db.get_bind(), checkfirst=True)
    code = data.code.strip().upper()
    if db.query(PromoCode).filter(PromoCode.code == code).first():
        raise HTTPException(400, "Код уже есть")
    p = PromoCode(
        code=code,
        discount_percent=max(0, min(90, data.discount_percent)),
        discount_fixed=Decimal(str(data.discount_fixed or 0)),
        max_uses=data.max_uses or 0,
        min_order_tjs=Decimal(str(data.min_order_tjs or 0)),
        note=data.note,
        is_active=data.is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/admin/{promo_id}")
def admin_delete(promo_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.owner))):
    p = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if not p:
        raise HTTPException(404)
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/check")
def check_promo(data: PromoCheck, db: Session = Depends(get_db)):
    PromoCode.__table__.create(bind=db.get_bind(), checkfirst=True)
    code = data.code.strip().upper()
    p = db.query(PromoCode).filter(PromoCode.code == code, PromoCode.is_active == True).first()
    if not p:
        raise HTTPException(400, "Промокод не найден")
    if p.expires_at and p.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Промокод истёк")
    if p.max_uses and p.used_count >= p.max_uses:
        raise HTTPException(400, "Лимит использований исчерпан")
    if data.subtotal < float(p.min_order_tjs or 0):
        raise HTTPException(400, f"Минимальная сумма заказа {p.min_order_tjs} TJS")
    discount = 0.0
    if p.discount_percent:
        discount = data.subtotal * p.discount_percent / 100.0
    if p.discount_fixed:
        discount = max(discount, float(p.discount_fixed))
    discount = min(discount, data.subtotal)
    return {
        "ok": True,
        "code": p.code,
        "discount": round(discount, 2),
        "discount_percent": p.discount_percent,
        "message": f"Скидка {round(discount, 0)} TJS",
    }


def apply_promo(db: Session, code: str | None, subtotal: Decimal) -> tuple[Decimal, str | None]:
    """Returns (discount_amount, code_or_none)."""
    if not code:
        return Decimal("0"), None
    PromoCode.__table__.create(bind=db.get_bind(), checkfirst=True)
    p = db.query(PromoCode).filter(PromoCode.code == code.strip().upper(), PromoCode.is_active == True).first()
    if not p:
        return Decimal("0"), None
    if p.max_uses and p.used_count >= p.max_uses:
        return Decimal("0"), None
    if subtotal < (p.min_order_tjs or 0):
        return Decimal("0"), None
    discount = Decimal("0")
    if p.discount_percent:
        discount = (subtotal * p.discount_percent / 100).quantize(Decimal("0.01"))
    if p.discount_fixed and p.discount_fixed > discount:
        discount = p.discount_fixed
    if discount > subtotal:
        discount = subtotal
    p.used_count = (p.used_count or 0) + 1
    return discount, p.code
