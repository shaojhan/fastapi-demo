from contextlib import asynccontextmanager
from uuid import uuid4
from typing import AsyncIterator, Callable
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.exceptions.BaseException import BaseException
from app.config import get_settings
from app.limiter import limiter
from app.telemetry import setup_telemetry, get_trace_context, shutdown_telemetry
import app.logger  # noqa: F401 — configures loguru format + file sink
import app.router

settings = get_settings()

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator:
    """Function that handles startup and shutdown events."""
    from app.services.MQTTClientManager import MQTTClientManager
    from app.services.KafkaClientManager import KafkaClientManager

    mqtt_manager = MQTTClientManager.get_instance()
    try:
        mqtt_manager.connect()
        logger.info("MQTT client connected")
    except Exception as e:
        logger.warning(f"MQTT connection failed (will retry automatically): {e}")

    kafka_manager = KafkaClientManager.get_instance()
    try:
        await kafka_manager.start()
        logger.info("Kafka client started")
    except Exception as e:
        logger.warning(f"Kafka connection failed (will retry on next request): {e}")

    yield

    await kafka_manager.stop()
    logger.info("Kafka client stopped")
    mqtt_manager.disconnect()
    logger.info("MQTT client disconnected")
    shutdown_telemetry()
    logger.info("OpenTelemetry shut down")

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

# Rate limiting
fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrict to configured origins; never use wildcard in production
_allowed_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Initialize OpenTelemetry (no-op when OTEL_ENABLED=False)
setup_telemetry(fastapi_app)

def create_exception_handler() -> Callable:
    async def exception_handler(_: Request, exc: BaseException) -> JSONResponse:
        logger.error(f"[{exc.name}]: {exc.message}")

        message = exc.message or "Unexpected error occurred!"

        if exc.name:
            message = f"{message} [{exc.name}]"

        content = {'detail': message}

        # Include error_code if present (for client-side handling)
        if exc.error_code:
            content['error_code'] = exc.error_code

        return JSONResponse(
            status_code=exc.status_code,
            content=content
        )
    return exception_handler

fastapi_app.add_exception_handler(
    exc_class_or_status_code=BaseException,
    handler=create_exception_handler()
)


@fastapi_app.middleware("http")
async def request_middleware(request, call_next):
    trace_ctx = get_trace_context()
    request_id = trace_ctx["trace_id"] or str(uuid4())
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