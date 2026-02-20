from datetime import datetime, timezone


class KafkaMessageModel:
    """Domain model representing a consumed Kafka message."""

    def __init__(
        self,
        id: int | None,
        topic: str,
        key: str | None,
        value: str,
        partition: int | None,
        offset: int | None,
        received_at: datetime,
    ):
        self._id = id
        self._topic = topic
        self._key = key
        self._value = value
        self._partition = partition
        self._offset = offset
        self._received_at = received_at

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def key(self) -> str | None:
        return self._key

    @property
    def value(self) -> str:
        return self._value

    @property
    def partition(self) -> int | None:
        return self._partition

    @property
    def offset(self) -> int | None:
        return self._offset

    @property
    def received_at(self) -> datetime:
        return self._received_at

    @staticmethod
    def create(
        topic: str,
        value: str,
        key: str | None = None,
        partition: int | None = None,
        offset: int | None = None,
    ) -> "KafkaMessageModel":
        if not topic:
            raise ValueError("Topic cannot be empty")
        return KafkaMessageModel(
            id=None,
            topic=topic,
            key=key,
            value=value,
            partition=partition,
            offset=offset,
            received_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def reconstitute(
        id: int,
        topic: str,
        value: str,
        key: str | None,
        partition: int | None,
        offset: int | None,
        received_at: datetime,
    ) -> "KafkaMessageModel":
        return KafkaMessageModel(
            id=id,
            topic=topic,
            key=key,
            value=value,
            partition=partition,
            offset=offset,
            received_at=received_at,
        )
