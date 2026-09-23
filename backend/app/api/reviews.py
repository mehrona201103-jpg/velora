"""Product reviews API."""
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.core.exceptions import NotFoundError, ValidationError
from app.models.product import Product
from app.models.order import Order, OrderItem

router = APIRouter()


# Inline model if not in models package yet
class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)
    text: str | None = None
    order_id: int | None = None


class ReviewOut(BaseModel):
    id: int
    product_id: int
    user_id: int
    rating: int
    text: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/product/{product_id}", response_model=list[ReviewOut])
async def list_product_reviews(product_id: int, db: DbSession):
    result = await db.execute(
        select(Review)
        .where(Review.product_id == product_id, Review.is_approved == True)  # noqa
        .order_by(Review.created_at.desc())
        .limit(50)
    )
    return [ReviewOut.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=ReviewOut, status_code=201)
async def create_review(data: ReviewCreate, user: CurrentUser, db: DbSession):
    pr = await db.execute(select(Product).where(Product.id == data.product_id))
    if not pr.scalar_one_or_none():
        raise NotFoundError("Товар не найден")
    review = Review(
        user_id=user.id,
        product_id=data.product_id,
        order_id=data.order_id,
        rating=data.rating,
        text=data.text,
        is_approved=True,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return ReviewOut.model_validate(review)
