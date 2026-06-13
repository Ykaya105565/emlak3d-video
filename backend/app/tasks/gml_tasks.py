from app.core.celery_app import celery_app
from loguru import logger


@celery_app.task(name="app.tasks.gml_tasks.parse_gml_task", bind=True, max_retries=3)
def parse_gml_task(self, listing_id: str, gml_key: str):
    """
    MinIO'dan GML indir → parse → oda envanteri → DB güncelle.
    Render worker (Python) buraya delege eder.
    """
    import asyncio
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.listing import Listing

    logger.info(f"GML parse başlıyor: listing={listing_id} key={gml_key}")

    try:
        # GML dosyasını indir
        import boto3
        from botocore.client import Config
        from app.core.config import settings
        import tempfile, os

        s3 = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

        with tempfile.NamedTemporaryFile(suffix=".gml", delete=False) as f:
            s3.download_fileobj(settings.minio_bucket_gml, gml_key, f)
            tmp_path = f.name

        # GML parse — render/src/gml/parse.py
        import sys, pathlib
        render_src = pathlib.Path(__file__).resolve().parents[4] / "render" / "src"
        if str(render_src) not in sys.path:
            sys.path.insert(0, str(render_src))
        from gml.parse import parse_gml_file
        inventory = parse_gml_file(tmp_path)
        os.unlink(tmp_path)

        # DB güncelle
        async def _update():
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Listing).where(Listing.id == listing_id))
                listing = result.scalar_one_or_none()
                if listing:
                    listing.gml_room_inventory = inventory
                    await db.commit()
                    logger.info(f"GML parse tamamlandı: {len(inventory.get('rooms', []))} oda")

        asyncio.run(_update())
        return {"status": "done", "rooms": len(inventory.get("rooms", []))}

    except Exception as exc:
        logger.error(f"GML parse hatası: {exc}")
        raise self.retry(exc=exc, countdown=30)
