from app.core.celery_app import celery_app
from loguru import logger
from datetime import datetime, timezone


@celery_app.task(name="app.tasks.render_tasks.render_video_task", bind=True, queue="render", max_retries=2)
def render_video_task(self, job_id: str):
    """
    VideoJob'u alır, render worker'a (Node.js/Remotion) gönderir.
    İlerlemeyi Redis üzerinden günceller.
    """
    import asyncio
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.video_job import VideoJob, VideoJobStatus
    from app.models.listing import Listing
    from app.core.config import settings
    import httpx

    logger.info(f"Render görevi başlıyor: job_id={job_id}")

    async def _run():
        async with AsyncSessionLocal() as db:
            job_result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = job_result.scalar_one_or_none()
            if not job:
                return

            listing_result = await db.execute(select(Listing).where(Listing.id == job.listing_id))
            listing = listing_result.scalar_one_or_none()

            job.status = VideoJobStatus.PROCESSING
            job.progress_pct = 5
            await db.commit()

        try:
            # Render worker (Node.js) HTTP API'sine render isteği gönder
            async with httpx.AsyncClient(timeout=600.0) as client:
                payload = {
                    "job_id": job_id,
                    "listing_id": job.listing_id,
                    "duration_seconds": job.duration_seconds,
                    "resolution": job.resolution,
                    "orientation": job.orientation,
                    "is_watermarked": job.is_watermarked,
                    "interior_source": listing.interior_source if listing else "listing_data",
                    "gml_file_key": listing.gml_file_key if listing else None,
                    "room_inventory": listing.gml_room_inventory if listing else None,
                    "lat": listing.lat if listing else None,
                    "lng": listing.lng if listing else None,
                    "listing_data": {
                        "title": listing.title if listing else "",
                        "listing_type": listing.listing_type if listing else "",
                        "city": listing.city if listing else "",
                        "address_text": listing.address_text if listing else "",
                        "gross_area": listing.gross_area if listing else None,
                        "net_area": listing.net_area if listing else None,
                        "room_count": listing.room_count if listing else None,
                        "floor": listing.floor if listing else None,
                        "total_floors": listing.total_floors if listing else None,
                        "price": listing.price if listing else None,
                        "currency": listing.currency if listing else "TRY",
                    }
                }
                r = await client.post(
                    f"{settings.render_worker_url}/render",
                    json=payload,
                )
                r.raise_for_status()
                result = r.json()

            async with AsyncSessionLocal() as db:
                job_result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = VideoJobStatus.COMPLETED
                    job.progress_pct = 100
                    job.output_file_key = result.get("output_key")
                    job.completed_at = datetime.now(timezone.utc)
                    job.scenario_text = result.get("scenario_text")
                    await db.commit()

        except Exception as exc:
            logger.error(f"Render hatası: {exc}")
            async with AsyncSessionLocal() as db:
                job_result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = VideoJobStatus.FAILED
                    job.error_message = str(exc)
                    await db.commit()
            raise

    asyncio.run(_run())
