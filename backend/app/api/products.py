from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.core.database import get_db
from app.models.product import Product, Category, ProductImage
from app.models.user import Role
from app.schemas.product import ProductOut, ProductListResponse, ProductCreate, ProductUpdate, CategoryOut
from app.api.deps import get_current_user, require_roles
from app.models.user import User

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).order_by(Category.sort_order).all()


@router.get("", response_model=ProductListResponse)
def list_products(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|popular|discount)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.variants),
    ).filter(Product.is_published == True)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Product.name_ru.ilike(like),
            Product.name_tj.ilike(like),
            Product.name_en.ilike(like),
            Product.sku.ilike(like),
        ))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "popular":
        query = query.order_by(Product.views.desc())
    elif sort == "discount":
        query = query.order_by(Product.discount_percent.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # Attach final_price
    result_items = []
    for p in items:
        out = ProductOut.model_validate(p)
        out.final_price = p.final_price
        result_items.append(out)

    return ProductListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if page_size else 1,
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.variants),
    ).filter(Product.id == product_id, Product.is_published == True).first()
    if not product:
        raise HTTPException(404, "Product not found")
    product.views += 1
    db.commit()
    out = ProductOut.model_validate(product)
    out.final_price = product.final_price
    return out


# Admin endpoints
@router.post("", response_model=ProductOut)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    if db.query(Product).filter(Product.sku == data.sku).first():
        raise HTTPException(400, "SKU already exists")
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    out = ProductOut.model_validate(product)
    out.final_price = product.final_price
    return out


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.owner)),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    out = ProductOut.model_validate(product)
    out.final_price = product.final_price
    return out
