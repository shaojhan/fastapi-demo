from loguru import logger
import logging

logger.add(
    './logs/fast-api-{time:YYYY-MM-DD}.log',
    level=logging.INFO,
    rotation='10 MB',
    retention='10 days',
    compression='zip',
)

