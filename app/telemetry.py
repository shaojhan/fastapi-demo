"""
OpenTelemetry initialization module.

Provides setup functions for tracing, instrumentation, and trace context helpers.
When OTEL_ENABLED is False, all functions are no-ops (zero overhead).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

_tracer_provider = None


def setup_telemetry(app: FastAPI) -> None:
    """
    Initialize OpenTelemetry for the FastAPI application.

    Sets up TracerProvider, OTLP exporter, and auto-instruments:
    FastAPI, SQLAlchemy, httpx, Redis, logging.

    Args:
        app: The FastAPI application instance
    """
    global _tracer_provider

    settings = get_settings()
    if not settings.OTEL_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor

    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME,
        "service.version": app.version,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy
    from app.db import engine
    SQLAlchemyInstrumentor().instrument(engine=engine)

    # Auto-instrument outgoing HTTP (httpx)
    HTTPXClientInstrumentor().instrument()

    # Auto-instrument Redis
    RedisInstrumentor().instrument()

    # Auto-instrument logging (adds trace context to log records)
    LoggingInstrumentor().instrument()


def setup_celery_telemetry() -> None:
    """
    Initialize OpenTelemetry for Celery workers.

    Uses a separate service name with '-worker' suffix.
    """
    global _tracer_provider

    settings = get_settings()
    if not settings.OTEL_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    resource = Resource.create({
        "service.name": f"{settings.OTEL_SERVICE_NAME}-worker",
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    CeleryInstrumentor().instrument()

    from app.db import engine
    SQLAlchemyInstrumentor().instrument(engine=engine)

    RedisInstrumentor().instrument()


def get_tracer(name: str = "fastapi-demo"):
    """
    Get an OpenTelemetry tracer.

    Returns a no-op tracer when OTEL_ENABLED is False.
    """
    from opentelemetry import trace
    return trace.get_tracer(name)


def get_trace_context() -> dict[str, str]:
    """
    Get current trace_id and span_id from the active span.

    Returns:
        Dict with trace_id and span_id (empty strings if no active span).
    """
    from opentelemetry import trace

    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    return {"trace_id": "", "span_id": ""}


def shutdown_telemetry() -> None:
    """Flush pending spans and shut down the tracer provider."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
