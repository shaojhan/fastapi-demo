from fastapi import APIRouter, Depends, Query

from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_admin
from app.router.schemas.KafkaSchema import (
    KafkaProduceRequest,
    KafkaProduceResponse,
    KafkaSubscribeRequest,
    KafkaSubscriptionResponse,
    KafkaStatusResponse,
    KafkaMessageItem,
    KafkaMessageListResponse,
)
from app.services.KafkaService import KafkaService
from app.exceptions.KafkaException import KafkaNotRunningError, KafkaProduceError


router = APIRouter(prefix='/kafka', tags=['kafka'])


def get_kafka_service() -> KafkaService:
    return KafkaService()


@router.get('/status', response_model=KafkaStatusResponse, operation_id='kafka_status')
def get_status(
    admin_user: UserModel = Depends(require_admin),
    service: KafkaService = Depends(get_kafka_service),
) -> KafkaStatusResponse:
    """Get Kafka connection status and active subscriptions."""
    status = service.get_status()
    return KafkaStatusResponse(**status)


@router.post('/produce', response_model=KafkaProduceResponse, operation_id='kafka_produce')
async def produce_message(
    request_body: KafkaProduceRequest,
    admin_user: UserModel = Depends(require_admin),
    service: KafkaService = Depends(get_kafka_service),
) -> KafkaProduceResponse:
    """Produce a message to a Kafka topic."""
    try:
        await service.produce(
            topic=request_body.topic,
            value=request_body.value,
            key=request_body.key,
        )
    except RuntimeError:
        raise KafkaNotRunningError()
    except Exception:
        raise KafkaProduceError()
    return KafkaProduceResponse(topic=request_body.topic, produced=True)


@router.post('/subscriptions', response_model=KafkaSubscriptionResponse, operation_id='kafka_subscribe')
async def subscribe_topic(
    request_body: KafkaSubscribeRequest,
    admin_user: UserModel = Depends(require_admin),
    service: KafkaService = Depends(get_kafka_service),
) -> KafkaSubscriptionResponse:
    """Subscribe to a Kafka topic."""
    try:
        await service.subscribe(topic=request_body.topic)
    except RuntimeError:
        raise KafkaNotRunningError()
    return KafkaSubscriptionResponse(topic=request_body.topic, subscribed=True)


@router.get('/subscriptions', response_model=list[str], operation_id='kafka_list_subscriptions')
def list_subscriptions(
    admin_user: UserModel = Depends(require_admin),
    service: KafkaService = Depends(get_kafka_service),
) -> list[str]:
    """List active Kafka subscriptions."""
    return service.get_status()["subscriptions"]


@router.delete('/subscriptions/{topic:path}', response_model=KafkaSubscriptionResponse, operation_id='kafka_unsubscribe')
async def unsubscribe_topic(
    topic: str,
    admin_user: UserModel = Depends(require_admin),
    service: KafkaService = Depends(get_kafka_service),
) -> KafkaSubscriptionResponse:
    """Unsubscribe from a Kafka topic."""
    try:
        await service.unsubscribe(topic=topic)
    except RuntimeError:
        raise KafkaNotRunningError()
    return KafkaSubscriptionResponse(topic=topic, subscribed=False)


@router.get('/messages', response_model=KafkaMessageListResponse, operation_id='kafka_list_messages')
def list_messages(
    topic: str | None = Query(None, description="Filter by topic"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    admin_user: UserModel = Depends(require_admin),
    service: KafkaService = Depends(get_kafka_service),
) -> KafkaMessageListResponse:
    """Query stored Kafka messages with optional topic filter and pagination."""
    messages, total = service.get_messages(topic=topic, page=page, size=size)
    items = [
        KafkaMessageItem(
            id=m.id,
            topic=m.topic,
            key=m.key,
            value=m.value,
            partition=m.partition,
            offset=m.offset,
            received_at=m.received_at,
        )
        for m in messages
    ]
    return KafkaMessageListResponse(items=items, total=total, page=page, size=size)
