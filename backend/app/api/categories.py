"""Categories API."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DbSession, require_permissions
from app.core.exceptions import ConflictError, NotFoundError
from app.models.product import Category
from app.models.user import User

router = APIRouter()


class CategoryOut(BaseModel):
    id: int
    name_ru: str
    name_tg: str | None
    name_en: str | None
    slug: str
    parent_id: int | None
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name_ru: str = Field(..., min_length=1)
    name_tg: str | None = None
    name_en: str | None = None
    slug: str = Field(..., min_length=1)
    parent_id: int | None = None
    sort_order: int = 0


@router.get("", response_model=list[CategoryOut])
async def list_categories(db: DbSession):
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order, Category.id)  # noqa
    )
    return [CategoryOut.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: DbSession,
    admin: User = Depends(require_permissions("products.write")),
):
    existing = await db.execute(select(Category).where(Category.slug == data.slug))
    if existing.scalar_one_or_none():
        raise ConflictError("Slug уже существует")
    cat = Category(
        name_ru=data.name_ru, name_tg=data.name_tg, name_en=data.name_en,
        slug=data.slug, parent_id=data.parent_id, sort_order=data.sort_order, is_active=True,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryOut.model_validate(cat)
