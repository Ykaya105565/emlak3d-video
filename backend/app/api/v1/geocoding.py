from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user
from app.services.geocoding_service import geocode_address
from app.models.user import User

router = APIRouter(prefix="/geocoding", tags=["geocoding"])


class GeocodeRequest(BaseModel):
    address: str
    city: Optional[str] = None


class GeocodeResponse(BaseModel):
    lat: float
    lng: float
    formatted_address: str
    provider: str  # "google" | "nominatim"
    confidence: float


@router.post("/", response_model=GeocodeResponse)
async def geocode(
    body: GeocodeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Adres → koordinat. Google birincil, Nominatim fallback.
    Sonuç kullanıcıya haritada gösterilir ve onaylatılır (confirm-location endpoint).
    """
    result = await geocode_address(body.address, body.city)
    if not result:
        raise HTTPException(status_code=404, detail="Adres bulunamadı")
    return result
