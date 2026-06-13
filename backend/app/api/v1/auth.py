from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token
from app.models.user import User
from app.models.tenant import Tenant
from app.models.credit import CreditWallet
from app.models.kvkk import KVKKConsent
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    kvkk_consent: bool  # KVKK onayı zorunlu


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if not body.kvkk_consent:
        raise HTTPException(status_code=400, detail="KVKK onayı zorunludur")

    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")

    slug = body.company_name.lower().replace(" ", "-")[:50] + "-" + str(uuid.uuid4())[:8]
    tenant = Tenant(name=body.company_name, slug=slug)
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_admin=True,
    )
    db.add(user)
    await db.flush()

    # Her yeni kiracı için kredi cüzdanı oluştur
    wallet = CreditWallet(tenant_id=tenant.id, balance=5.0)  # 5 başlangıç kredisi
    db.add(wallet)

    consent = KVKKConsent(
        user_id=user.id,
        tenant_id=tenant.id,
        consent_type="registration",
        is_granted=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, tenant.id),
        refresh_token=create_refresh_token(user.id, tenant.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hesap devre dışı")

    return TokenResponse(
        access_token=create_access_token(user.id, user.tenant_id),
        refresh_token=create_refresh_token(user.id, user.tenant_id),
    )
