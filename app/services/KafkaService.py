from typing import List, Tuple

from app.domain.KafkaModel import KafkaMessageModel
from app.services.unitofwork.KafkaUnitOfWork import KafkaUnitOfWork
from app.services.KafkaClientManager import KafkaClientManager


class KafkaService:
    """Application service for Kafka operations."""

    def handle_message(
        self,
        topic: str,
        value: str,
        key: str | None = None,
        partition: int | None = None,
        offset: int | None = None,
    ) -> None:
        """Store a consumed Kafka message in the database."""
        message = KafkaMessageModel.create(
            topic=topic, value=value, key=key, partition=partition, offset=offset,
        )
        with KafkaUnitOfWork() as uow:
            uow.repo.add(message)
            uow.commit()

    def get_messages(
        self,
        topic: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[KafkaMessageModel], int]:
        """Query stored Kafka messages with optional topic filter."""
        with KafkaUnitOfWork() as uow:
            return uow.repo.get_messages(topic=topic, page=page, size=size)

    async def produce(self, topic: str, value: str, key: str | None = None) -> None:
        """Produce a message to a Kafka topic."""
        manager = KafkaClientManager.get_instance()
        await manager.produce(topic, value, key)

    async def subscribe(self, topic: str) -> None:
        """Subscribe to a Kafka topic."""
        manager = KafkaClientManager.get_instance()
        await manager.subscribe(topic)

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a Kafka topic."""
        manager = KafkaClientManager.get_instance()
        await manager.unsubscribe(topic)

    def get_status(self) -> dict:
        """Get Kafka connection status."""
        manager = KafkaClientManager.get_instance()
        return {
            "running": manager.is_running,
            "subscriptions": manager.subscriptions,
        }
