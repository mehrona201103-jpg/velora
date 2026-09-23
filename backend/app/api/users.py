"""User profile endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel
from decimal import Decimal
from sqlalchemy import select
from app.core.deps import CurrentUser, DbSession
from app.models.finance import Balance

router = APIRouter()


class UserMeResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str
    email: str | None
    language: str
    roles: list[str]
    balance: Decimal

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserMeResponse)
async def get_me(user: CurrentUser, db: DbSession):
    result = await db.execute(select(Balance).where(Balance.user_id == user.id))
    balance = result.scalar_one_or_none()
    amount = balance.amount if balance else Decimal("0.00")
    return UserMeResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        language=user.language,
        roles=[r.name for r in user.roles],
        balance=amount,
    )
