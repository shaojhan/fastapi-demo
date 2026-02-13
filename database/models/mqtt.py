from datetime import datetime

from sqlalchemy import BigInteger, String, Text, Integer, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MQTTMessage(Base):
    __tablename__ = "mqtt_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=True)
    qos: Mapped[int] = mapped_column(Integer, default=0)
    received_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_mqtt_messages_topic", "topic"),
        Index("idx_mqtt_messages_received_at", "received_at"),
    )
