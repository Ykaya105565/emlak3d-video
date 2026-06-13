import httpx
from typing import Optional
from app.core.config import settings
from loguru import logger


async def geocode_address(address: str, city: Optional[str] = None) -> Optional[dict]:
    """
    Google Geocoding birincil, Nominatim fallback.
    Sonuç kullanıcı tarafından haritada onaylanmadan kesinleşmez.
    """
    query = f"{address}, {city}, Türkiye" if city else f"{address}, Türkiye"

    if settings.google_maps_api_key:
        result = await _google_geocode(query)
        if result:
            return result

    logger.warning("Google Geocoding başarısız, Nominatim'e geçiliyor")
    return await _nominatim_geocode(query)


async def _google_geocode(query: str) -> Optional[dict]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": settings.google_maps_api_key, "language": "tr", "region": "TR"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "OK" and data.get("results"):
                res = data["results"][0]
                loc = res["geometry"]["location"]
                return {
                    "lat": loc["lat"],
                    "lng": loc["lng"],
                    "formatted_address": res["formatted_address"],
                    "provider": "google",
                    "confidence": 0.95,
                }
    except Exception as e:
        logger.error(f"Google Geocoding hatası: {e}")
    return None


async def _nominatim_geocode(query: str) -> Optional[dict]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "tr"}
    headers = {"User-Agent": "EmlakPlatform/1.0 (contact@example.com)"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
            if data:
                item = data[0]
                return {
                    "lat": float(item["lat"]),
                    "lng": float(item["lon"]),
                    "formatted_address": item.get("display_name", query),
                    "provider": "nominatim",
                    "confidence": float(item.get("importance", 0.5)),
                }
    except Exception as e:
        logger.error(f"Nominatim Geocoding hatası: {e}")
    return None
