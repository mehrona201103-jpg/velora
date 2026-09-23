"""Admin product management (create/update)."""
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DbSession, require_permissions
from app.core.exceptions import NotFoundError
from app.models.product import Product, ProductVariant, Category, Color, Size
from app.models.inventory import Inventory
from app.models.user import User

router = APIRouter()


class ProductCreate(BaseModel):
    name_ru: str = Field(..., min_length=1, max_length=255)
    name_tg: str | None = None
    name_en: str | None = None
    description_ru: str | None = None
    sku: str = Field(..., min_length=1, max_length=50)
    category_id: int | None = None
    base_price: Decimal = Field(..., gt=0)
    old_price: Decimal | None = None
    is_featured: bool = False
    is_new: bool = False
    size_chart: str | None = None
    # Simple single variant for quick create
    initial_stock: int = Field(0, ge=0)
    color_id: int | None = None
    size_id: int | None = None


class ProductOut(BaseModel):
    id: int
    name_ru: str
    sku: str
    base_price: Decimal
    is_active: bool

    class Config:
        from_attributes = True


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    data: ProductCreate,
    db: DbSession,
    admin: User = Depends(require_permissions("products.write")),
):
    # Check SKU unique
    existing = await db.execute(select(Product).where(Product.sku == data.sku))
    if existing.scalar_one_or_none():
        from app.core.exceptions import ConflictError
        raise ConflictError("SKU уже существует")

    product = Product(
        name_ru=data.name_ru,
        name_tg=data.name_tg,
        name_en=data.name_en,
        description_ru=data.description_ru,
        sku=data.sku,
        category_id=data.category_id,
        base_price=data.base_price,
        old_price=data.old_price,
        is_featured=data.is_featured,
        is_new=data.is_new,
        size_chart=data.size_chart,
        is_active=True,
    )
    db.add(product)
    await db.flush()

    # Create default variant
    variant = ProductVariant(
        product_id=product.id,
        color_id=data.color_id,
        size_id=data.size_id,
        sku=f"{data.sku}-DEFAULT",
        is_active=True,
    )
    db.add(variant)
    await db.flush()

    # Inventory
    inv = Inventory(variant_id=variant.id, quantity=data.initial_stock, reserved=0)
    db.add(inv)

    await db.commit()
    await db.refresh(product)
    return ProductOut.model_validate(product)


@router.get("/admin/list", response_model=list[ProductOut])
async def admin_list_products(
    db: DbSession,
    admin: User = Depends(require_permissions("products.read")),
):
    result = await db.execute(select(Product).order_by(Product.created_at.desc()).limit(100))
    return [ProductOut.model_validate(p) for p in result.scalars().all()]
