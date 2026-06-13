from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_id
from app.models.credit import CreditWallet, CreditTransaction
from app.models.user import User

router = APIRouter(prefix="/credits", tags=["credits"])


class WalletResponse(BaseModel):
    balance: float
    tenant_id: str


class TransactionResponse(BaseModel):
    id: str
    transaction_type: str
    amount: float
    description: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/wallet", response_model=WalletResponse)
async def get_wallet(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CreditWallet).where(CreditWallet.tenant_id == tenant_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Cüzdan bulunamadı")
    return WalletResponse(balance=wallet.balance, tenant_id=tenant_id)


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.tenant_id == tenant_id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        return []

    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(50)
    )
    txs = result.scalars().all()
    return [
        TransactionResponse(
            id=t.id,
            transaction_type=t.transaction_type,
            amount=t.amount,
            description=t.description,
            created_at=t.created_at.isoformat(),
        )
        for t in txs
    ]
