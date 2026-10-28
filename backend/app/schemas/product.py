from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: int
    name_ru: str
    name_tj: Optional[str] = None
    name_en: Optional[str] = None
    slug: str
    image_url: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ProductImageOut(BaseModel):
    id: int
    url: str
    alt: Optional[str] = None
    is_main: bool

    model_config = {"from_attributes": True}


class ProductVariantOut(BaseModel):
    id: int
    name: str
    price_modifier: Decimal
    stock: int
    is_active: bool

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    sku: str
    name_ru: str
    name_tj: Optional[str] = None
    name_en: Optional[str] = None
    description_ru: Optional[str] = None
    category_id: Optional[int] = None
    price: Decimal
    discount_percent: int
    final_price: Decimal
    stock: int
    is_published: bool
    delivery_days_min: int
    delivery_days_max: int
    rating_avg: Decimal
    rating_count: int
    images: List[ProductImageOut] = []
    variants: List[ProductVariantOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    sku: str
    name_ru: str
    name_tj: Optional[str] = None
    name_en: Optional[str] = None
    description_ru: Optional[str] = None
    category_id: Optional[int] = None
    purchase_price: Decimal = 0
    price: Decimal
    discount_percent: int = 0
    stock: int = 0
    is_published: bool = False
    delivery_days_min: int = 14
    delivery_days_max: int = 30


class ProductUpdate(BaseModel):
    name_ru: Optional[str] = None
    name_tj: Optional[str] = None
    name_en: Optional[str] = None
    description_ru: Optional[str] = None
    category_id: Optional[int] = None
    purchase_price: Optional[Decimal] = None
    price: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    stock: Optional[int] = None
    is_published: Optional[bool] = None
    delivery_days_min: Optional[int] = None
    delivery_days_max: Optional[int] = None


class ProductListResponse(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int
    pages: int
