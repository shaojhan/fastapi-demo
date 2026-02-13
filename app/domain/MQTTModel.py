from datetime import datetime, timezone


class MQTTMessageModel:
    """Domain model representing a received MQTT message."""

    def __init__(
        self,
        id: int | None,
        topic: str,
        payload: str,
        qos: int,
        received_at: datetime,
    ):
        self._id = id
        self._topic = topic
        self._payload = payload
        self._qos = qos
        self._received_at = received_at

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def payload(self) -> str:
        return self._payload

    @property
    def qos(self) -> int:
        return self._qos

    @property
    def received_at(self) -> datetime:
        return self._received_at

    @staticmethod
    def create(topic: str, payload: str, qos: int = 0) -> "MQTTMessageModel":
        if not topic:
            raise ValueError("Topic cannot be empty")
        return MQTTMessageModel(
            id=None,
            topic=topic,
            payload=payload,
            qos=qos,
            received_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def reconstitute(
        id: int,
        topic: str,
        payload: str,
        qos: int,
        received_at: datetime,
    ) -> "MQTTMessageModel":
        return MQTTMessageModel(
            id=id,
            topic=topic,
            payload=payload,
            qos=qos,
            received_at=received_at,
        )
