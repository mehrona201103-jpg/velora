"""Products catalog API."""
from decimal import Decimal
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.deps import DbSession, OptionalUser
from app.core.exceptions import NotFoundError
from app.models.product import Product, ProductImage, ProductVariant, Category

router = APIRouter()


class ProductImageOut(BaseModel):
    id: int
    storage_key: str
    alt_text: str | None
    is_primary: bool

    class Config:
        from_attributes = True


class ProductListItem(BaseModel):
    id: int
    name_ru: str
    sku: str
    base_price: Decimal
    old_price: Decimal | None
    is_featured: bool
    is_new: bool
    primary_image: str | None = None
    default_variant_id: int | None = None

    class Config:
        from_attributes = True


class ProductDetail(BaseModel):
    id: int
    name_ru: str
    name_tg: str | None
    name_en: str | None
    description_ru: str | None
    sku: str
    base_price: Decimal
    old_price: Decimal | None
    size_chart: str | None
    is_active: bool
    images: list[ProductImageOut] = []

    class Config:
        from_attributes = True


class PaginatedProducts(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("", response_model=PaginatedProducts)
async def list_products(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    search: str | None = None,
    is_new: bool | None = None,
    is_featured: bool | None = None,
):
    q = select(Product).where(Product.is_active == True)  # noqa: E712
    count_q = select(func.count(Product.id)).where(Product.is_active == True)  # noqa: E712

    if category_id:
        q = q.where(Product.category_id == category_id)
        count_q = count_q.where(Product.category_id == category_id)
    if search:
        like = f"%{search}%"
        q = q.where(Product.name_ru.ilike(like) | Product.sku.ilike(like))
        count_q = count_q.where(Product.name_ru.ilike(like) | Product.sku.ilike(like))
    if is_new is not None:
        q = q.where(Product.is_new == is_new)
        count_q = count_q.where(Product.is_new == is_new)
    if is_featured is not None:
        q = q.where(Product.is_featured == is_featured)
        count_q = count_q.where(Product.is_featured == is_featured)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.options(
        selectinload(Product.images),
        selectinload(Product.variants),
    ).order_by(Product.created_at.desc())
    q = q.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    products = result.scalars().all()

    items = []
    for p in products:
        primary = next((img.storage_key for img in p.images if img.is_primary), None)
        if not primary and p.images:
            primary = p.images[0].storage_key
        default_variant = next((v for v in p.variants if v.is_active), None)
        items.append(
            ProductListItem(
                id=p.id,
                name_ru=p.name_ru,
                sku=p.sku,
                base_price=p.base_price,
                old_price=p.old_price,
                is_featured=p.is_featured,
                is_new=p.is_new,
                primary_image=primary,
                default_variant_id=default_variant.id if default_variant else None,
            )
        )

    pages = (total + per_page - 1) // per_page if per_page else 0
    return PaginatedProducts(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: int, db: DbSession):
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.images))
        .where(Product.id == product_id, Product.is_active == True)  # noqa: E712
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Товар не найден")
    return ProductDetail(
        id=product.id,
        name_ru=product.name_ru,
        name_tg=product.name_tg,
        name_en=product.name_en,
        description_ru=product.description_ru,
        sku=product.sku,
        base_price=product.base_price,
        old_price=product.old_price,
        size_chart=product.size_chart,
        is_active=product.is_active,
        images=[ProductImageOut.model_validate(img) for img in product.images],
    )
