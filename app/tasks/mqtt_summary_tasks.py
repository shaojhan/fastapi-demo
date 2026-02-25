import asyncio

from celery import shared_task
from loguru import logger

from app.services.MQTTSummaryService import MQTTSummaryService


@shared_task(
    bind=True,
    name="mqtt.summary.daily_digest",
    max_retries=0,
    ignore_result=False,
)
def send_mqtt_summary_task(self, hours: int | None = None) -> dict:
    """
    Celery task: generate and distribute the MQTT daily digest.

    Can be triggered by Celery beat (no args, uses MQTT_SUMMARY_HOURS from
    config) or by an admin via REST API (with explicit hours override).

    Args:
        hours: Optional look-back window override in hours.

    Returns:
        Dict with message_count, recipient_count, sent_count, failed_count.
    """
    logger.info(f"Starting MQTT summary task (hours={hours})")
    service = MQTTSummaryService()
    try:
        result = asyncio.run(service.generate_and_send(hours=hours))
        logger.info(f"MQTT summary task completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"MQTT summary task failed: {exc}")
        raise
