"""Balance, top-up, refund models. Money uses NUMERIC."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Balance(Base):
    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="balance")
    transactions: Mapped[list["BalanceTransaction"]] = relationship(back_populates="balance")


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance_id: Mapped[int] = mapped_column(ForeignKey("balances.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # CREDIT, DEBIT, REFUND, BONUS, DELIVERY
    reference_type: Mapped[str | None] = mapped_column(String(50))  # order, topup, refund
    reference_id: Mapped[int | None] = mapped_column()
    balance_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # who performed
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    balance: Mapped[Balance] = relationship(back_populates="transactions")


class PaymentTopUpRequest(Base):
    __tablename__ = "payment_topup_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    receipt_storage_key: Mapped[str | None] = mapped_column(String(500))
    comment: Mapped[str | None] = mapped_column(Text)
    admin_comment: Mapped[str | None] = mapped_column(Text)
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topup_request_id: Mapped[int] = mapped_column(ForeignKey("payment_topup_requests.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="REQUESTED")  # REQUESTED, APPROVED, PROCESSING, COMPLETED, REJECTED
    reason: Mapped[str | None] = mapped_column(Text)
    admin_comment: Mapped[str | None] = mapped_column(Text)
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


from app.models.user import User  # noqa: E402
