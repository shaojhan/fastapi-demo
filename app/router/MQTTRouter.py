from fastapi import APIRouter, Depends, Query

from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_admin
from app.router.schemas.MQTTSchema import (
    MQTTPublishRequest,
    MQTTPublishResponse,
    MQTTSubscribeRequest,
    MQTTSubscriptionResponse,
    MQTTStatusResponse,
    MQTTMessageItem,
    MQTTMessageListResponse,
    MQTTSummaryTriggerRequest,
    MQTTSummaryTriggerResponse,
)
from app.services.MQTTService import MQTTService
from app.exceptions.MQTTException import MQTTNotConnectedError, MQTTPublishError
from app.tasks.mqtt_summary_tasks import send_mqtt_summary_task


router = APIRouter(prefix='/mqtt', tags=['mqtt'])


def get_mqtt_service() -> MQTTService:
    return MQTTService()


@router.get('/status', response_model=MQTTStatusResponse, operation_id='mqtt_status')
def get_status(
    admin_user: UserModel = Depends(require_admin),
    service: MQTTService = Depends(get_mqtt_service),
) -> MQTTStatusResponse:
    """Get MQTT connection status and active subscriptions."""
    status = service.get_status()
    return MQTTStatusResponse(**status)


@router.post('/publish', response_model=MQTTPublishResponse, operation_id='mqtt_publish')
def publish_message(
    request_body: MQTTPublishRequest,
    admin_user: UserModel = Depends(require_admin),
    service: MQTTService = Depends(get_mqtt_service),
) -> MQTTPublishResponse:
    """Publish a message to an MQTT topic."""
    try:
        service.publish(
            topic=request_body.topic,
            payload=request_body.payload,
            qos=request_body.qos,
        )
    except RuntimeError:
        raise MQTTNotConnectedError()
    except Exception:
        raise MQTTPublishError()
    return MQTTPublishResponse(topic=request_body.topic, published=True)


@router.post('/subscriptions', response_model=MQTTSubscriptionResponse, operation_id='mqtt_subscribe')
def subscribe_topic(
    request_body: MQTTSubscribeRequest,
    admin_user: UserModel = Depends(require_admin),
    service: MQTTService = Depends(get_mqtt_service),
) -> MQTTSubscriptionResponse:
    """Subscribe to an MQTT topic."""
    try:
        service.subscribe(topic=request_body.topic, qos=request_body.qos)
    except RuntimeError:
        raise MQTTNotConnectedError()
    return MQTTSubscriptionResponse(topic=request_body.topic, subscribed=True)


@router.get('/subscriptions', response_model=list[str], operation_id='mqtt_list_subscriptions')
def list_subscriptions(
    admin_user: UserModel = Depends(require_admin),
    service: MQTTService = Depends(get_mqtt_service),
) -> list[str]:
    """List active MQTT subscriptions."""
    return service.get_status()["subscriptions"]


@router.delete('/subscriptions/{topic:path}', response_model=MQTTSubscriptionResponse, operation_id='mqtt_unsubscribe')
def unsubscribe_topic(
    topic: str,
    admin_user: UserModel = Depends(require_admin),
    service: MQTTService = Depends(get_mqtt_service),
) -> MQTTSubscriptionResponse:
    """Unsubscribe from an MQTT topic."""
    try:
        service.unsubscribe(topic=topic)
    except RuntimeError:
        raise MQTTNotConnectedError()
    return MQTTSubscriptionResponse(topic=topic, subscribed=False)


@router.get('/messages', response_model=MQTTMessageListResponse, operation_id='mqtt_list_messages')
def list_messages(
    topic: str | None = Query(None, description="Filter by topic"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    admin_user: UserModel = Depends(require_admin),
    service: MQTTService = Depends(get_mqtt_service),
) -> MQTTMessageListResponse:
    """Query stored MQTT messages with optional topic filter and pagination."""
    messages, total = service.get_messages(topic=topic, page=page, size=size)
    items = [
        MQTTMessageItem(
            id=m.id,
            topic=m.topic,
            payload=m.payload,
            qos=m.qos,
            received_at=m.received_at,
        )
        for m in messages
    ]
    return MQTTMessageListResponse(items=items, total=total, page=page, size=size)


@router.post('/summary/trigger', response_model=MQTTSummaryTriggerResponse, operation_id='mqtt_trigger_summary')
def trigger_summary(
    request_body: MQTTSummaryTriggerRequest,
    admin_user: UserModel = Depends(require_admin),
) -> MQTTSummaryTriggerResponse:
    """Manually trigger the MQTT daily digest task.

    Enqueues the summary task immediately and returns a task_id.
    Use GET /tasks/status/{task_id} to poll for completion.
    """
    task = send_mqtt_summary_task.delay(hours=request_body.hours)
    return MQTTSummaryTriggerResponse(
        task_id=task.id,
        hours=request_body.hours,
        message=f"Summary task queued for the past {request_body.hours} hour(s).",
    )
