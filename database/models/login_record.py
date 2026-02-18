from app.db import Base

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Uuid,
    String,
    DateTime,
    Boolean,
    func,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from uuid import UUID


class LoginRecord(Base):
    __tablename__ = "login_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('ix_login_records_user_id', 'user_id'),
        Index('ix_login_records_created_at', 'created_at'),
    )
