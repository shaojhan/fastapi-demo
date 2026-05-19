import time

from app.tasks import celery_app


@celery_app.task(name="demo.very_long_task")
def very_long_task():
    print("Start calculating...")
    start_time = time.time()
    time.sleep(1)
    end_time = time.time()
    print("Calculate completed!")
    time_delta = end_time - start_time
    return {"execute time": f"{time_delta}"}


@celery_app.task(name="demo.add")
def add(x, y):
    return x + y
