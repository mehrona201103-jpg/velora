"""Internal balance and top-up endpoints."""
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_permissions
from app.core.exceptions import NotFoundError, IdempotencyError, ValidationError
from app.models.finance import Balance, BalanceTransaction, PaymentTopUpRequest
from app.models.system import AuditLog
from app.models.user import User

router = APIRouter()


class BalanceResponse(BaseModel):
    amount: Decimal
    currency: str = "TJS"


class TopUpCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    comment: str | None = None
    idempotency_key: str | None = None


class TopUpResponse(BaseModel):
    id: int
    amount: Decimal
    status: str
    created_at: datetime
    comment: str | None = None
    admin_comment: str | None = None

    class Config:
        from_attributes = True


class AdminTopUpAction(BaseModel):
    admin_comment: str | None = None


@router.get("", response_model=BalanceResponse)
async def get_balance(user: CurrentUser, db: DbSession):
    result = await db.execute(select(Balance).where(Balance.user_id == user.id))
    balance = result.scalar_one_or_none()
    amount = balance.amount if balance else Decimal("0.00")
    return BalanceResponse(amount=amount)


@router.post("/topup", response_model=TopUpResponse, status_code=201)
async def create_topup(data: TopUpCreate, user: CurrentUser, db: DbSession):
    if data.idempotency_key:
        existing = await db.execute(
            select(PaymentTopUpRequest).where(
                PaymentTopUpRequest.idempotency_key == data.idempotency_key
            )
        )
        if existing.scalar_one_or_none():
            raise IdempotencyError("Заявка с таким ключом уже существует")

    req = PaymentTopUpRequest(
        user_id=user.id,
        amount=data.amount,
        comment=data.comment,
        idempotency_key=data.idempotency_key,
        status="PENDING",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return TopUpResponse.model_validate(req)


@router.get("/topup", response_model=list[TopUpResponse])
async def list_my_topups(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(PaymentTopUpRequest)
        .where(PaymentTopUpRequest.user_id == user.id)
        .order_by(PaymentTopUpRequest.created_at.desc())
        .limit(50)
    )
    return [TopUpResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/admin/topups/pending", response_model=list[TopUpResponse])
async def admin_pending_topups(
    db: DbSession,
    admin: User = Depends(require_permissions("payments.approve")),
):
    result = await db.execute(
        select(PaymentTopUpRequest)
        .where(PaymentTopUpRequest.status == "PENDING")
        .order_by(PaymentTopUpRequest.created_at.asc())
        .limit(100)
    )
    return [TopUpResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/admin/topups/{request_id}/approve", response_model=TopUpResponse)
async def approve_topup(
    request_id: int,
    data: AdminTopUpAction,
    db: DbSession,
    admin: User = Depends(require_permissions("payments.approve")),
):
    result = await db.execute(
        select(PaymentTopUpRequest).where(PaymentTopUpRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise NotFoundError("Заявка не найдена")
    if req.status != "PENDING":
        raise IdempotencyError("Заявка уже обработана")

    # Credit balance atomically
    bal_result = await db.execute(
        select(Balance).where(Balance.user_id == req.user_id).with_for_update()
    )
    balance = bal_result.scalar_one_or_none()
    if not balance:
        balance = Balance(user_id=req.user_id, amount=Decimal("0.00"))
        db.add(balance)
        await db.flush()

    before = balance.amount
    balance.amount = before + req.amount
    after = balance.amount

    tx = BalanceTransaction(
        balance_id=balance.id,
        user_id=req.user_id,
        amount=req.amount,
        type="CREDIT",
        reference_type="topup",
        reference_id=req.id,
        balance_before=before,
        balance_after=after,
        actor_id=admin.id,
        description=f"Пополнение баланса #{req.id}",
    )
    db.add(tx)

    req.status = "APPROVED"
    req.admin_comment = data.admin_comment
    req.processed_by = admin.id
    req.processed_at = datetime.now(timezone.utc)

    audit = AuditLog(
        actor_id=admin.id,
        action="topup.approve",
        object_type="PaymentTopUpRequest",
        object_id=req.id,
        new_value=str(req.amount),
    )
    db.add(audit)

    await db.commit()
    await db.refresh(req)
    return TopUpResponse.model_validate(req)


@router.post("/admin/topups/{request_id}/reject", response_model=TopUpResponse)
async def reject_topup(
    request_id: int,
    data: AdminTopUpAction,
    db: DbSession,
    admin: User = Depends(require_permissions("payments.approve")),
):
    result = await db.execute(
        select(PaymentTopUpRequest).where(PaymentTopUpRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise NotFoundError("Заявка не найдена")
    if req.status != "PENDING":
        raise IdempotencyError("Заявка уже обработана")

    req.status = "REJECTED"
    req.admin_comment = data.admin_comment
    req.processed_by = admin.id
    req.processed_at = datetime.now(timezone.utc)

    audit = AuditLog(
        actor_id=admin.id,
        action="topup.reject",
        object_type="PaymentTopUpRequest",
        object_id=req.id,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(req)
    return TopUpResponse.model_validate(req)
