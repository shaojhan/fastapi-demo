from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MQTTBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class MQTTPublishRequest(MQTTBaseModel):
    topic: str = Field(..., min_length=1, description="MQTT topic to publish to")
    payload: str = Field(..., description="Message payload")
    qos: int = Field(1, ge=0, le=2, description="Quality of Service (0, 1, 2)")


class MQTTSubscribeRequest(MQTTBaseModel):
    topic: str = Field(..., min_length=1, description="MQTT topic to subscribe to")
    qos: int = Field(1, ge=0, le=2, description="Quality of Service (0, 1, 2)")


class MQTTStatusResponse(MQTTBaseModel):
    connected: bool
    subscriptions: list[str]


class MQTTPublishResponse(MQTTBaseModel):
    topic: str
    published: bool


class MQTTSubscriptionResponse(MQTTBaseModel):
    topic: str
    subscribed: bool


class MQTTMessageItem(MQTTBaseModel):
    id: int
    topic: str
    payload: str
    qos: int
    received_at: datetime


class MQTTMessageListResponse(MQTTBaseModel):
    items: list[MQTTMessageItem]
    total: int
    page: int
    size: int
