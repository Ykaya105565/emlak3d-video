from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_id
from app.models.listing import Listing, ListingType, InteriorSourceType
from app.models.user import User
import uuid

router = APIRouter(prefix="/listings", tags=["listings"])


class ListingCreate(BaseModel):
    title: str
    listing_type: ListingType
    price: Optional[float] = None
    currency: str = "TRY"
    address_text: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    ada: Optional[str] = None
    parsel: Optional[str] = None
    takbis_no: Optional[str] = None
    gross_area: Optional[float] = None
    net_area: Optional[float] = None
    room_count: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_age: Optional[int] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_balcony: Optional[bool] = None
    description: Optional[str] = None
    # Villa Hayali (arsa)
    taks: Optional[float] = None
    kaks: Optional[float] = None
    setback_front: Optional[float] = None
    setback_side: Optional[float] = None
    max_floors: Optional[int] = None


class ListingResponse(BaseModel):
    id: str
    title: str
    listing_type: str
    price: Optional[float]
    city: Optional[str]
    district: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    interior_source: Optional[str]
    has_3d_coverage: Optional[bool]
    gml_room_inventory: Optional[dict]

    class Config:
        from_attributes = True


@router.post("/", response_model=ListingResponse)
async def create_listing(
    body: ListingCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    listing = Listing(
        tenant_id=tenant_id,
        owner_id=current_user.id,
        **body.model_dump(),
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


@router.get("/", response_model=List[ListingResponse])
async def list_listings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Listing)
        .where(Listing.tenant_id == tenant_id, Listing.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == tenant_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")
    return listing


@router.patch("/{listing_id}/confirm-location")
async def confirm_location(
    listing_id: str,
    lat: float,
    lng: float,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcı haritada konumu onaylar."""
    result = await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.tenant_id == tenant_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    listing.lat = lat
    listing.lng = lng
    listing.geocoding_confirmed = True
    await db.commit()
    return {"status": "confirmed", "lat": lat, "lng": lng}
