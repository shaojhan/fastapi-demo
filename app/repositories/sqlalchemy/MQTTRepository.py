from typing import Optional, List, Tuple

from .BaseRepository import BaseRepository
from database.models.mqtt import MQTTMessage
from app.domain.MQTTModel import MQTTMessageModel


class MQTTMessageRepository(BaseRepository):
    """Repository for MQTT message persistence."""

    def add(self, message: MQTTMessageModel) -> MQTTMessageModel:
        entity = MQTTMessage(
            topic=message.topic,
            payload=message.payload,
            qos=message.qos,
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
    ) -> Tuple[List[MQTTMessageModel], int]:
        query = self.db.query(MQTTMessage)

        if topic:
            query = query.filter(MQTTMessage.topic == topic)

        total = query.count()
        messages = (
            query.order_by(MQTTMessage.received_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return [self._to_domain(m) for m in messages], total

    def _to_domain(self, entity: MQTTMessage) -> MQTTMessageModel:
        return MQTTMessageModel.reconstitute(
            id=entity.id,
            topic=entity.topic,
            payload=entity.payload or "",
            qos=entity.qos,
            received_at=entity.received_at,
        )
