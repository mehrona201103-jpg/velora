from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.order import OrderStatus, PaymentStatus


class CartItemAdd(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(ge=1, default=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    product_name: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    model_config = {"from_attributes": True}


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut] = []
    subtotal: Decimal = Decimal("0")
    items_count: int = 0


class OrderCreate(BaseModel):
    product_id: Optional[int] = None  # direct buy
    variant_id: Optional[int] = None
    quantity: int = 1
    delivery_type: str = "home"  # home | office
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_phone: Optional[str] = None
    delivery_zone_id: Optional[int] = None
    payment_method_id: Optional[int] = None
    payment_method_code: Optional[str] = None  # dc | eskhata | tg_stars
    promo_code: Optional[str] = None
    customer_comment: Optional[str] = None
    # if from cart
    from_cart: bool = False


class OrderItemOut(BaseModel):
    product_id: Optional[int] = None
    id: int
    product_name: str
    variant_name: Optional[str] = None
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    model_config = {"from_attributes": True}


class OrderStatusHistoryOut(BaseModel):
    status: OrderStatus
    comment: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class PaymentSubmissionOut(BaseModel):
    id: int
    file_path: str
    original_filename: Optional[str] = None
    created_at: datetime
    is_reviewed: bool
    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal: Decimal
    delivery_cost: Decimal
    delivery_quote_status: Optional[str] = "none"
    discount_amount: Decimal
    total: Decimal
    delivery_address: str
    delivery_city: str
    delivery_phone: Optional[str] = None
    customer_comment: Optional[str] = None
    payment_rejection_reason: Optional[str] = None
    payment_method_id: Optional[int] = None
    items: List[OrderItemOut] = []
    status_history: List[OrderStatusHistoryOut] = []
    payment_submissions: List[PaymentSubmissionOut] = []
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class PaymentMethodOut(BaseModel):
    id: int
    code: Optional[str] = None
    name: str
    recipient_name: str
    account_number: Optional[str] = None
    instructions: Optional[str] = None
    tg_username: Optional[str] = None
    tg_deep_link: Optional[str] = None
    is_active: bool
    model_config = {"from_attributes": True}


class DeliveryZoneOut(BaseModel):
    id: int
    name: str
    city: str
    district: Optional[str] = None
    base_price: Decimal
    free_from_amount: Optional[Decimal] = None
    estimated_days_min: int
    estimated_days_max: int
    is_active: bool
    delivery_type: str
    model_config = {"from_attributes": True}
