from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "emlak_render",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_routes={
        "app.tasks.render.*": {"queue": "render"},
        "app.tasks.*": {"queue": "default"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])
