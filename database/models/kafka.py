from datetime import datetime

from sqlalchemy import BigInteger, String, Text, Integer, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class KafkaMessage(Base):
    __tablename__ = "kafka_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    partition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offset: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_kafka_messages_topic", "topic"),
        Index("idx_kafka_messages_received_at", "received_at"),
    )
