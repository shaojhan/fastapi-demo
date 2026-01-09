from contextlib import asynccontextmanager
from uuid import uuid4
from typing import AsyncIterator, Callable
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import logging

from app.exceptions.BaseException import BaseException
from app.config import get_settings
import app.router

logger.add(
    './logs/fast-api-{time:YYYY-MM-DD}.log',
    level=logging.INFO,
    rotation='10 MB',
    retention='10 days',
    compression='zip',
)

settings = get_settings()

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator:
    """Function that handles startup and shutdown events."""
    yield

fastapi_app = FastAPI(
    debug=False,
    title=f'{settings.FASTAPI_TITLE}-{settings.FASTAPI_ENV}',
    description="FastAPI Demo",
    version="0.3.4",
    lifespan=lifespan,
    root_path='/api',
    swagger_ui_parameters={
        #Core
        'url': 'openapi.json',
        'queryConfigEnabled': True,
        
        #Display
        'deepLinking': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 0,
        'defaultModelExpandDepth': 0,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'requestSnippetsEnabled': True,
    }
)

fastapi_app.include_router(router=app.router.router)
fastapi_app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

def create_exception_handler() -> Callable:
    async def exception_handler(_: Request, exc: BaseException) -> JSONResponse:
        logger.error(f"[{exc.name}]: {exc.message}")
        
        message = exc.message or "Unexpected error occurred!"
        
        if exc.name:
            # detail['message'] = f"{detail['message']} [{exc.name}]"
            message = f"{message} [{exc.name}]"
        
        return JSONResponse(
            status_code=exc.status_code,
            content={'detail': message}
        )
    return exception_handler

fastapi_app.add_exception_handler(
    exc_class_or_status_code=BaseException,
    handler=create_exception_handler()
)


@fastapi_app.middleware("http")
async def request_middleware(request, call_next):
    request_id = str(uuid4())
    with logger.contextualize(request_id=request_id):
        logger.info("Request started")
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(f"Request failed: {exc}")
            return JSONResponse(content={"success": False}, status_code=500)
        finally:
            logger.info("Request ended")


@fastapi_app.get('/', include_in_schema=False)
def hello(request: Request) -> dict:
    return {
        "message": "Hello World",
        "root_path": request.scope.get("root_path"),
    }

@fastapi_app.get('/root')
def read_root(settings = Depends(get_settings)):
    return {
        "app_name": settings.FASTAPI_TITLE,
        "debug": settings.debug,
        "mode": settings.FASTAPI_ENV
    }