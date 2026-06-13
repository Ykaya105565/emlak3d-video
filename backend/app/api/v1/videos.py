from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_id
from app.models.listing import Listing, InteriorSourceType
from app.models.video_job import VideoJob, VideoJobStatus, VideoResolution, VideoOrientation
from app.models.credit import CreditWallet
from app.models.user import User
from app.services.credit_service import calculate_credit_cost, deduct_credits
from app.core.storage import get_presigned_url
from app.core.config import settings

router = APIRouter(prefix="/videos", tags=["videos"])


class VideoRequest(BaseModel):
    listing_id: str
    duration_seconds: int = 30          # 15 | 30 | 60 | 90
    resolution: VideoResolution = VideoResolution.HD_1080P
    orientation: VideoOrientation = VideoOrientation.LANDSCAPE
    is_watermarked: bool = True         # True = ücretsiz deneme


class VideoJobResponse(BaseModel):
    id: str
    status: str
    progress_pct: int
    credit_cost: float
    is_watermarked: bool
    output_url: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/render", response_model=VideoJobResponse)
async def request_render(
    body: VideoRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Listing).where(Listing.id == body.listing_id, Listing.tenant_id == tenant_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")
    if not listing.geocoding_confirmed:
        raise HTTPException(status_code=400, detail="Konum haritada onaylanmadan video üretilemez")

    interior_source = listing.interior_source or InteriorSourceType.LISTING_DATA
    cost = calculate_credit_cost(
        duration=body.duration_seconds,
        resolution=body.resolution,
        interior_source=interior_source,
        is_watermarked=body.is_watermarked,
    )

    if not body.is_watermarked:
        wallet_result = await db.execute(
            select(CreditWallet).where(CreditWallet.tenant_id == tenant_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if not wallet or wallet.balance < cost:
            raise HTTPException(status_code=402, detail="Yetersiz kredi")
        await deduct_credits(db, wallet, cost, body.listing_id)

    job = VideoJob(
        listing_id=body.listing_id,
        tenant_id=tenant_id,
        duration_seconds=body.duration_seconds,
        resolution=body.resolution,
        orientation=body.orientation,
        credit_cost=cost,
        is_watermarked=body.is_watermarked,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Render görevi kuyruğa al
    from app.tasks.render_tasks import render_video_task
    task = render_video_task.delay(job.id)
    job.celery_task_id = task.id
    await db.commit()

    return VideoJobResponse(
        id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        credit_cost=cost,
        is_watermarked=job.is_watermarked,
    )


@router.get("/{job_id}", response_model=VideoJobResponse)
async def get_job_status(
    job_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.tenant_id == tenant_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Video işi bulunamadı")

    output_url = None
    if job.status == VideoJobStatus.COMPLETED and job.output_file_key:
        output_url = get_presigned_url(settings.minio_bucket_videos, job.output_file_key)

    return VideoJobResponse(
        id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        credit_cost=job.credit_cost,
        is_watermarked=job.is_watermarked,
        output_url=output_url,
    )
