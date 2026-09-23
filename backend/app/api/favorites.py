"""Favorites API."""
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError, ConflictError
from app.models.cart import Favorite
from app.models.product import Product

router = APIRouter()


class FavoriteOut(BaseModel):
    id: int
    product_id: int
    name_ru: str
    base_price: Decimal
    sku: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[FavoriteOut])
async def list_favorites(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())
    )
    favs = result.scalars().all()
    out = []
    for f in favs:
        pr = await db.execute(select(Product).where(Product.id == f.product_id))
        p = pr.scalar_one_or_none()
        if p:
            out.append(FavoriteOut(
                id=f.id, product_id=p.id, name_ru=p.name_ru,
                base_price=p.base_price, sku=p.sku,
            ))
    return out


@router.post("/{product_id}", response_model=FavoriteOut, status_code=201)
async def add_favorite(product_id: int, user: CurrentUser, db: DbSession):
    pr = await db.execute(select(Product).where(Product.id == product_id, Product.is_active == True))  # noqa
    p = pr.scalar_one_or_none()
    if not p:
        raise NotFoundError("Товар не найден")
    existing = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product_id)
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Уже в избранном")
    fav = Favorite(user_id=user.id, product_id=product_id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return FavoriteOut(id=fav.id, product_id=p.id, name_ru=p.name_ru, base_price=p.base_price, sku=p.sku)


@router.delete("/{product_id}", status_code=204)
async def remove_favorite(product_id: int, user: CurrentUser, db: DbSession):
    await db.execute(
        delete(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product_id)
    )
    await db.commit()
    return None
