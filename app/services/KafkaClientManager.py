from __future__ import annotations

import asyncio

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from loguru import logger

from app.config import get_settings


class KafkaClientManager:
    """Singleton manager for Kafka producer/consumer lifecycle."""

    _instance: KafkaClientManager | None = None

    def __init__(self):
        self._producer: AIOKafkaProducer | None = None
        self._consumer: AIOKafkaConsumer | None = None
        self._consumer_task: asyncio.Task | None = None
        self._running: bool = False
        self._subscriptions: set[str] = set()

    @classmethod
    def get_instance(cls) -> KafkaClientManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start Kafka producer. Consumer starts when topics are subscribed."""
        settings = get_settings()
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID,
        )
        await self._producer.start()
        self._running = True
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        """Stop Kafka producer and consumer."""
        self._running = False

        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None

        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Kafka consumer stopped")

        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    async def produce(self, topic: str, value: str, key: str | None = None) -> None:
        """Send a message to a Kafka topic."""
        if not self._producer:
            raise RuntimeError("Kafka producer is not started")
        key_bytes = key.encode("utf-8") if key else None
        await self._producer.send_and_wait(
            topic,
            value=value.encode("utf-8"),
            key=key_bytes,
        )

    async def subscribe(self, topic: str) -> None:
        """Subscribe to a topic and (re)start the consumer loop."""
        self._subscriptions.add(topic)
        await self._restart_consumer()
        logger.info(f"Kafka subscribed to topic: {topic}")

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic and restart the consumer loop."""
        self._subscriptions.discard(topic)
        await self._restart_consumer()
        logger.info(f"Kafka unsubscribed from topic: {topic}")

    async def _restart_consumer(self) -> None:
        """Stop the current consumer and start a new one with updated topics."""
        # Stop existing consumer
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if self._consumer:
            await self._consumer.stop()
            self._consumer = None

        if not self._subscriptions:
            return

        settings = get_settings()
        self._consumer = AIOKafkaConsumer(
            *self._subscriptions,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._consumer_task = asyncio.create_task(self._consume_loop())

    async def _consume_loop(self) -> None:
        """Background loop that consumes messages and delegates to KafkaService."""
        try:
            async for msg in self._consumer:
                topic = msg.topic
                value = msg.value.decode("utf-8", errors="replace") if msg.value else ""
                key = msg.key.decode("utf-8", errors="replace") if msg.key else None
                logger.info(f"Kafka message received: {topic} -> {value[:100]}")

                try:
                    from app.services.KafkaService import KafkaService

                    service = KafkaService()
                    service.handle_message(
                        topic=topic,
                        value=value,
                        key=key,
                        partition=msg.partition,
                        offset=msg.offset,
                    )
                except Exception as e:
                    logger.error(f"Failed to handle Kafka message on {topic}: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Kafka consumer loop error: {e}")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def subscriptions(self) -> list[str]:
        return sorted(self._subscriptions)
