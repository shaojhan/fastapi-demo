import time

from celery import shared_task


@shared_task(name="demo.very_long_task")
def very_long_task():
    print("Start calculating...")
    start_time = time.time()
    time.sleep(1)
    end_time = time.time()
    print("Calculate completed!")
    time_delta = end_time - start_time
    return {"execute time": f"{time_delta}"}


@shared_task(name="demo.add")
def add(x, y):
    return x + y
