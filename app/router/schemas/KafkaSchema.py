from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KafkaBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class KafkaProduceRequest(KafkaBaseModel):
    topic: str = Field(..., min_length=1, description="Kafka topic to produce to")
    value: str = Field(..., description="Message value (payload)")
    key: str | None = Field(None, description="Optional message key for partitioning")


class KafkaSubscribeRequest(KafkaBaseModel):
    topic: str = Field(..., min_length=1, description="Kafka topic to subscribe to")


class KafkaStatusResponse(KafkaBaseModel):
    running: bool
    subscriptions: list[str]


class KafkaProduceResponse(KafkaBaseModel):
    topic: str
    produced: bool


class KafkaSubscriptionResponse(KafkaBaseModel):
    topic: str
    subscribed: bool


class KafkaMessageItem(KafkaBaseModel):
    id: int
    topic: str
    key: str | None
    value: str
    partition: int | None
    offset: int | None
    received_at: datetime


class KafkaMessageListResponse(KafkaBaseModel):
    items: list[KafkaMessageItem]
    total: int
    page: int
    size: int
