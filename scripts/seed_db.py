#!/usr/bin/env python3
"""
Geliştirme ortamı için örnek veri tohumu.
Kullanım: python scripts/seed_db.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def seed():
    from app.core.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.credit import CreditWallet
    from app.core.security import hash_password
    import uuid

    async with AsyncSessionLocal() as db:
        # Demo tenant
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Demo Emlak Ofisi",
            slug="demo-emlak",
        )
        db.add(tenant)
        await db.flush()

        user = User(
            tenant_id=tenant.id,
            email="demo@example.com",
            hashed_password=hash_password("demo1234"),
            full_name="Demo Kullanıcı",
            is_admin=True,
        )
        db.add(user)
        await db.flush()

        wallet = CreditWallet(tenant_id=tenant.id, balance=20.0)
        db.add(wallet)

        await db.commit()
        print(f"Demo hesap oluşturuldu:")
        print(f"  E-posta : demo@example.com")
        print(f"  Şifre   : demo1234")
        print(f"  Kredi   : 20.0")


if __name__ == "__main__":
    asyncio.run(seed())
