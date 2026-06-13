from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import router as v1_router
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Emlak 3D Platform başlatılıyor...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Platform kapatılıyor...")
    await engine.dispose()


app = FastAPI(
    title="Emlak 3D Video Platformu",
    description="Türkiye geneli emlakçı platformu — CityGML iç mekân + fotorealistik dış 3D video",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
