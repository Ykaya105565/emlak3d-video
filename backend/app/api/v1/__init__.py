from fastapi import APIRouter
from app.api.v1 import auth, listings, uploads, videos, geocoding, credits

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(listings.router)
router.include_router(uploads.router)
router.include_router(videos.router)
router.include_router(geocoding.router)
router.include_router(credits.router)
