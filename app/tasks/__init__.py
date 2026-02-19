from celery import Celery
from celery.signals import worker_process_init

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])


@worker_process_init.connect
def init_worker(**kwargs):
    """Dispose stale DB connections and initialize OTel after worker fork."""
    from app.db import engine
    engine.dispose()

    from app.telemetry import setup_celery_telemetry
    setup_celery_telemetry()
