from app.db import Base

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Uuid,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    func,
    Index,
)
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)

if TYPE_CHECKING:
    from .user import User


class Schedule(Base):
    """
    排程 ORM 模型
    支援員工建立排程並同步到 Google Calendar
    """
    __tablename__ = "schedules"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    # 排程內容
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # 時間設定
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    timezone: Mapped[str] = mapped_column(String(64), default='Asia/Taipei', server_default='Asia/Taipei')

    # 建立者
    creator_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Google Calendar 同步
    google_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 關聯
    creator: Mapped["User"] = relationship("User", lazy="selectin")

    # 索引優化查詢
    __table_args__ = (
        Index('ix_schedules_creator_id', 'creator_id'),
        Index('ix_schedules_start_time', 'start_time'),
        Index('ix_schedules_end_time', 'end_time'),
    )


class GoogleCalendarConfig(Base):
    """
    Google Calendar 系統級設定
    儲存公司 Google Calendar 的 OAuth tokens
    """
    __tablename__ = "google_calendar_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    # Google Calendar 設定
    calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
