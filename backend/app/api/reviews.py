from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.models.user import User, Role
from app.models.product import Product
from app.models.order import Order, OrderItem, PaymentStatus
from app.models.review import Review
from app.models.support import SupportTicket, SupportMessage  # reuse pattern
from app.api.deps import get_current_user, get_current_user_optional, require_roles
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from app.core.database import Base

router = APIRouter(prefix="/products", tags=["reviews"])


# Lightweight product chat messages (Pinduoduo-style)
class ProductComment(Base):
    __tablename__ = "product_comments"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    text = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_staff = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    rating: int
    text: Optional[str] = None
    user_name: Optional[str] = None
    is_verified_buyer: bool = False
    created_at: datetime
    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    image_url: Optional[str] = None


class CommentOut(BaseModel):
    id: int
    text: str
    image_url: Optional[str] = None
    user_name: Optional[str] = None
    is_staff: bool = False
    created_at: datetime


@router.get("/{product_id}/reviews")
def list_reviews(product_id: int, db: Session = Depends(get_db)):
    rows = db.query(Review).filter(Review.product_id == product_id, Review.is_approved == True).order_by(Review.created_at.desc()).limit(50).all()
    result = []
    for r in rows:
        u = db.query(User).filter(User.id == r.user_id).first()
        result.append({
            "id": r.id,
            "rating": r.rating,
            "text": r.text,
            "user_name": (u.full_name or u.email or "Покупатель") if u else "Покупатель",
            "is_verified_buyer": bool(r.order_id),
            "image_url": getattr(r, "image_url", None),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return result


@router.post("/{product_id}/reviews")
def create_review(
    product_id: int,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Товар не найден")

    # Must have paid order with this product
    paid_item = (
        db.query(OrderItem)
        .join(Order)
        .filter(
            Order.user_id == user.id,
            Order.payment_status == PaymentStatus.paid,
            OrderItem.product_id == product_id,
        )
        .first()
    )
    if not paid_item:
        raise HTTPException(400, "Отзыв можно оставить только после оплаченного заказа этого товара")

    existing = db.query(Review).filter(Review.product_id == product_id, Review.user_id == user.id).first()
    if existing:
        raise HTTPException(400, "Вы уже оставили отзыв на этот товар")

    review = Review(
        product_id=product_id,
        user_id=user.id,
        order_id=paid_item.order_id,
        rating=data.rating,
        text=data.text,
        is_approved=True,  # auto-approve for MVP; admin can moderate later
    )
    db.add(review)
    db.flush()

    # Update product rating
    avg, cnt = db.query(func.avg(Review.rating), func.count(Review.id)).filter(
        Review.product_id == product_id, Review.is_approved == True
    ).first()
    product.rating_avg = Decimal(str(round(float(avg or 0), 2)))
    product.rating_count = int(cnt or 0)
    db.commit()
    return {"ok": True, "rating_avg": float(product.rating_avg), "rating_count": product.rating_count}


@router.get("/{product_id}/comments")
def list_comments(product_id: int, db: Session = Depends(get_db)):
    # ensure table exists
    ProductComment.__table__.create(bind=db.get_bind(), checkfirst=True)
    rows = db.query(ProductComment).filter(ProductComment.product_id == product_id).order_by(ProductComment.created_at.desc()).limit(100).all()
    result = []
    for c in rows:
        u = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "text": c.text,
            "image_url": c.image_url,
            "user_name": (u.full_name or "Пользователь") if u else "Пользователь",
            "is_staff": c.is_staff,
            "is_verified": bool(u and u.is_verified) if u else False,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return result


@router.post("/{product_id}/comments")
def create_comment(
    product_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ProductComment.__table__.create(bind=db.get_bind(), checkfirst=True)
    product = db.query(Product).filter(Product.id == product_id, Product.is_published == True).first()
    if not product:
        raise HTTPException(404, "Товар не найден")
    if len(data.text.strip()) < 1:
        raise HTTPException(400, "Пустое сообщение")
    c = ProductComment(
        product_id=product_id,
        user_id=user.id,
        text=data.text.strip()[:1000],
        image_url=data.image_url,
        is_staff=user.role in (Role.owner, Role.admin, Role.support),
    )
    db.add(c)
    db.commit()
    return {"ok": True, "id": c.id}


from fastapi import File, UploadFile, Form
from app.services.media_store import save_bytes_db

@router.post("/{product_id}/reviews/with-photo")
async def create_review_with_photo(
    product_id: int,
    rating: int = Form(...),
    text: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if rating < 1 or rating > 5:
        raise HTTPException(400, "Оценка 1–5")
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Товар не найден")
    paid_item = (
        db.query(OrderItem).join(Order)
        .filter(Order.user_id == user.id, Order.payment_status == PaymentStatus.paid, OrderItem.product_id == product_id)
        .first()
    )
    if not paid_item:
        raise HTTPException(400, "Отзыв только после оплаченного заказа")
    existing = db.query(Review).filter(Review.product_id == product_id, Review.user_id == user.id).first()
    if existing:
        raise HTTPException(400, "Вы уже оставили отзыв")
    image_url = None
    if file and file.filename:
        content = await file.read()
        if len(content) > 8 * 1024 * 1024:
            raise HTTPException(400, "Файл слишком большой")
        image_url = save_bytes_db(db, content, f"rev_{user.id}_{product_id}.jpg", file.content_type)
    review = Review(
        product_id=product_id,
        user_id=user.id,
        order_id=paid_item.order_id,
        rating=rating,
        text=text or None,
        image_url=image_url,
        is_approved=True,
    )
    db.add(review)
    db.flush()
    avg, cnt = db.query(func.avg(Review.rating), func.count(Review.id)).filter(
        Review.product_id == product_id, Review.is_approved == True
    ).first()
    product.rating_avg = Decimal(str(round(float(avg or 0), 2)))
    product.rating_count = int(cnt or 0)
    db.commit()
    return {"ok": True, "rating_avg": float(product.rating_avg), "rating_count": product.rating_count}
