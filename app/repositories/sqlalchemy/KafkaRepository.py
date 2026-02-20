from typing import List, Tuple

from .BaseRepository import BaseRepository
from database.models.kafka import KafkaMessage
from app.domain.KafkaModel import KafkaMessageModel


class KafkaMessageRepository(BaseRepository):
    """Repository for Kafka message persistence."""

    def add(self, message: KafkaMessageModel) -> KafkaMessageModel:
        entity = KafkaMessage(
            topic=message.topic,
            key=message.key,
            value=message.value,
            partition=message.partition,
            offset=message.offset,
            received_at=message.received_at,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return self._to_domain(entity)

    def get_messages(
        self,
        topic: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[KafkaMessageModel], int]:
        query = self.db.query(KafkaMessage)

        if topic:
            query = query.filter(KafkaMessage.topic == topic)

        total = query.count()
        messages = (
            query.order_by(KafkaMessage.received_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return [self._to_domain(m) for m in messages], total

    def _to_domain(self, entity: KafkaMessage) -> KafkaMessageModel:
        return KafkaMessageModel.reconstitute(
            id=entity.id,
            topic=entity.topic,
            key=entity.key,
            value=entity.value or "",
            partition=entity.partition,
            offset=entity.offset,
            received_at=entity.received_at,
        )
