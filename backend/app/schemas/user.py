from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str = Field(min_length=6)
    full_name: Optional[str] = None
    device_type: str = Field(..., pattern="^(phone|tablet|pc)$")
    referral_code: Optional[str] = None  # чужой код при регистрации


class UserLogin(BaseModel):
    login: str
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    device_type: Optional[str] = None
    lock_type: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    language: str = "ru"
    device_type: str = "phone"
    avatar_url: Optional[str] = None
    is_verified: bool = False
    verification_status: str = "none"
    total_orders: int = 0
    total_spent: Decimal = Decimal("0")
    lock_type: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    loyalty_points: int = 0
    referral_code: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AddressCreate(BaseModel):
    title: str = "Дом"
    city: str
    district: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    apartment: Optional[str] = None
    full_address: str
    phone: Optional[str] = None
    is_default: bool = False


class AddressOut(AddressCreate):
    id: int
    user_id: int
    model_config = {"from_attributes": True}


class VerificationSubmit(BaseModel):
    full_name: str
    age_confirmed: bool = True
