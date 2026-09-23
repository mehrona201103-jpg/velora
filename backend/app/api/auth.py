"""Authentication endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.exceptions import UnauthorizedError, ConflictError, ValidationError
from app.models.user import User, Role
from app.models.finance import Balance
from decimal import Decimal

router = APIRouter()


class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=9, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if data.password != data.password_confirm:
        raise ValidationError("Пароли не совпадают")

    # Check existing phone
    result = await db.execute(select(User).where(User.phone == data.phone))
    if result.scalar_one_or_none():
        raise ConflictError("Пользователь с таким телефоном уже существует")

    # Create user
    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.flush()

    # Assign CLIENT role
    role_result = await db.execute(select(Role).where(Role.name == "CLIENT"))
    client_role = role_result.scalar_one_or_none()
    if client_role:
        user.roles.append(client_role)

    # Create zero balance
    balance = Balance(user_id=user.id, amount=Decimal("0.00"))
    db.add(balance)

    await db.commit()

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Неверный телефон или пароль")

    if not user.is_active:
        raise UnauthorizedError("Аккаунт деактивирован")

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)
