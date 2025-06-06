from celery import Celery
import time

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "worker",
    broker=settings.BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

@celery_app.task
def very_long_task():
    print("Start calculating...")
    startTime = time.time()
    time.sleep(1)
    endTime = time.time()
    print("Calculate completed!")
    timeDelta = endTime - startTime
    return {"execute time": f"{timeDelta}"}


@celery_app.task
def add(x, y):
    return x + y

