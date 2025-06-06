from fastapi import APIRouter, HTTPException

from celery.result import AsyncResult
from ..tasks import celery_app, very_long_task

from uuid import uuid4
import time

router = APIRouter(prefix='/tasks', tags=['task'])

@router.get('/result/{task_id}')
def get_task_result(task_id: str):
    result = AsyncResult(id=task_id, app=celery_app)
    if result.ready():
        return {"status": result.status, "result": result.result}
    return {"status": result.status}


@router.get('/add')
async def enqueue_add():
    task = very_long_task.delay()
    return {"task_id": task.id}