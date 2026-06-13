from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_id
from app.core.storage import upload_file, get_presigned_url
from app.core.config import settings
from app.models.listing import Listing, ListingMedia, InteriorSourceType
from app.models.kvkk import KVKKConsent
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_GML_TYPES = {"application/xml", "text/xml", "application/gml+xml"}
ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_GML_SIZE = 100 * 1024 * 1024   # 100 MB
MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/gml/{listing_id}")
async def upload_gml(
    listing_id: str,
    request: Request,
    file: UploadFile = File(...),
    kvkk_consent: bool = Form(...),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    CityGML dosyası yükle. KVKK onayı zorunlu.
    Yükleme sonrasında GML parse görevi kuyruğa alınır.
    """
    if not kvkk_consent:
        raise HTTPException(status_code=400, detail="GML yükleme için KVKK onayı zorunludur")

    result = await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == tenant_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    data = await file.read()
    if len(data) > MAX_GML_SIZE:
        raise HTTPException(status_code=413, detail="GML dosyası 100 MB'ı aşamaz")

    # KVKK kaydı
    consent = KVKKConsent(
        user_id=current_user.id,
        tenant_id=tenant_id,
        consent_type="gml_upload",
        resource_id=listing_id,
        is_granted=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)
    await db.flush()

    key = f"{tenant_id}/{listing_id}/gml/{uuid.uuid4()}.gml"
    upload_file(settings.minio_bucket_gml, key, data, "application/xml")

    media = ListingMedia(
        listing_id=listing_id,
        file_key=key,
        media_type="gml",
        original_filename=file.filename,
        kvkk_consent_id=consent.id,
    )
    db.add(media)

    listing.gml_file_key = key
    listing.interior_source = InteriorSourceType.GML_3D
    await db.commit()

    # GML parse görevi kuyruğa al
    from app.tasks.gml_tasks import parse_gml_task
    parse_gml_task.delay(listing_id, key)

    return {"status": "uploaded", "key": key, "parse_status": "queued"}


@router.post("/photos/{listing_id}")
async def upload_photos(
    listing_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
    kvkk_consent: bool = Form(...),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Fotoğraf yükle (çoklu). KVKK onayı zorunlu."""
    if not kvkk_consent:
        raise HTTPException(status_code=400, detail="Fotoğraf yükleme için KVKK onayı zorunludur")

    result = await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == tenant_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    consent = KVKKConsent(
        user_id=current_user.id,
        tenant_id=tenant_id,
        consent_type="photo_upload",
        resource_id=listing_id,
        is_granted=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)
    await db.flush()

    uploaded = []
    for i, f in enumerate(files):
        data = await f.read()
        if len(data) > MAX_PHOTO_SIZE:
            continue
        key = f"{tenant_id}/{listing_id}/photos/{uuid.uuid4()}{_ext(f.filename)}"
        upload_file(settings.minio_bucket_photos, key, data, f.content_type or "image/jpeg")
        media = ListingMedia(
            listing_id=listing_id,
            file_key=key,
            media_type="photo",
            original_filename=f.filename,
            sort_order=i,
            kvkk_consent_id=consent.id,
        )
        db.add(media)
        uploaded.append(key)

    # GML yoksa kaynak fotoğraf olarak ayarla
    if listing.interior_source != InteriorSourceType.GML_3D and uploaded:
        listing.interior_source = InteriorSourceType.PHOTOS

    await db.commit()
    return {"uploaded": len(uploaded), "keys": uploaded}


def _ext(filename: Optional[str]) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ".jpg"
