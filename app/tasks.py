from celery import Celery

celery_app = Celery(
    "worker",
    broker="redis://localhost:6739/0",
    backend="redis://localhost:6739/0"
)

@celery_app.task
def add(x, y):
    return x + y

