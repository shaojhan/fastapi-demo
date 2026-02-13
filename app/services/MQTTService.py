from typing import List, Tuple

from loguru import logger

from app.domain.MQTTModel import MQTTMessageModel
from app.services.unitofwork.MQTTUnitOfWork import MQTTUnitOfWork
from app.services.MQTTClientManager import MQTTClientManager


class MQTTService:
    """Application service for MQTT operations."""

    def handle_message(self, topic: str, payload: str, qos: int = 0) -> None:
        """Store a received MQTT message in the database."""
        message = MQTTMessageModel.create(topic=topic, payload=payload, qos=qos)
        with MQTTUnitOfWork() as uow:
            uow.repo.add(message)
            uow.commit()

    def get_messages(
        self,
        topic: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[MQTTMessageModel], int]:
        """Query stored MQTT messages with optional topic filter."""
        with MQTTUnitOfWork() as uow:
            return uow.repo.get_messages(topic=topic, page=page, size=size)

    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        """Publish a message to an MQTT topic."""
        manager = MQTTClientManager.get_instance()
        manager.publish(topic, payload, qos)

    def subscribe(self, topic: str, qos: int = 1) -> None:
        """Subscribe to an MQTT topic."""
        manager = MQTTClientManager.get_instance()
        manager.subscribe(topic, qos)

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from an MQTT topic."""
        manager = MQTTClientManager.get_instance()
        manager.unsubscribe(topic)

    def get_status(self) -> dict:
        """Get MQTT connection status."""
        manager = MQTTClientManager.get_instance()
        return {
            "connected": manager.is_connected,
            "subscriptions": manager.subscriptions,
        }
