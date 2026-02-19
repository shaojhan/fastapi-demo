from loguru import logger
import logging


def _trace_id_patcher(record):
    """Inject trace_id from OpenTelemetry into loguru log records."""
    from app.telemetry import get_trace_context
    ctx = get_trace_context()
    record["extra"].setdefault("trace_id", ctx["trace_id"] or "-")


# Apply patcher globally so ALL loguru calls (including from other modules) get trace_id
logger.configure(patcher=_trace_id_patcher)

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{extra[trace_id]} | {name}:{function}:{line} | {message}"
)

logger.add(
    './logs/fast-api-{time:YYYY-MM-DD}.log',
    level=logging.INFO,
    format=LOG_FORMAT,
    rotation='10 MB',
    retention='10 days',
    compression='zip',
)
