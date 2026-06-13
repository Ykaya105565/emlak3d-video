import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    CONSUME = "consume"
    REFUND = "refund"
    BONUS = "bonus"


class CreditWallet(Base):
    __tablename__ = "credit_wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="wallet")
    transactions: Mapped[list["CreditTransaction"]] = relationship("CreditTransaction", back_populates="wallet")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("credit_wallets.id"), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    video_job_id: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    wallet: Mapped["CreditWallet"] = relationship("CreditWallet", back_populates="transactions")
