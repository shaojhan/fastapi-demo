from fastapi import APIRouter, HTTPException

from celery.result import AsyncResult
from ..tasks import celery_app

router = APIRouter(prefix='/tasks', tags=['task'])