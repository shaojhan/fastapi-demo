from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from app.router.schemas.TaskSchema import (
    TaskCancelResponse,
    TaskProgressInfo,
    TaskStatusResponse,
)
from app.services.BackgroundTaskPublisher import (
    BackgroundTaskPublisher,
    CeleryBackgroundTaskPublisher,
)
from app.tasks import celery_app

router = APIRouter(prefix='/tasks', tags=['task'])


def get_background_task_publisher() -> BackgroundTaskPublisher:
    return CeleryBackgroundTaskPublisher()


@router.get('/status/{task_id}', response_model=TaskStatusResponse, operation_id='get_task_status')
def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the current status and progress of a background task."""
    result = AsyncResult(id=task_id, app=celery_app)
    status = result.status

    progress = None
    task_result = None
    error = None

    if status == "PROGRESS":
        meta = result.info or {}
        progress = TaskProgressInfo(
            current=meta.get("current", 0),
            total=meta.get("total", 0),
            percent=meta.get("percent", 0.0),
            current_idno=meta.get("current_idno"),
        )
    elif status == "SUCCESS":
        task_result = result.result
    elif status == "FAILURE":
        error = str(result.info) if result.info else "Unknown error"

    return TaskStatusResponse(
        task_id=task_id,
        status=status,
        progress=progress,
        result=task_result,
        error=error,
    )


@router.delete('/cancel/{task_id}', response_model=TaskCancelResponse, operation_id='cancel_task')
def cancel_task(task_id: str) -> TaskCancelResponse:
    """Cancel a running or pending task."""
    result = AsyncResult(id=task_id, app=celery_app)
    result.revoke(terminate=True, signal="SIGTERM")
    return TaskCancelResponse(task_id=task_id, cancelled=True)


@router.get('/add', operation_id='enqueue_demo_add')
async def enqueue_add(
    task_publisher: BackgroundTaskPublisher = Depends(get_background_task_publisher),
):
    """Demo endpoint: enqueue a long-running test task."""
    return {"task_id": task_publisher.enqueue_demo_task()}
