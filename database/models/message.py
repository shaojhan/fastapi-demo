from app.db import Base

from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
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


class Message(Base):
    """
    留言 ORM 模型
    支援父子留言關係（回覆功能）和已讀狀態追蹤
    """
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    # 留言內容
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 發送者與接收者
    sender_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 回覆功能：父留言 ID（NULL 表示原始留言）
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )

    # 已讀狀態
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 軟刪除支援
    deleted_by_sender: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    deleted_by_recipient: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')

    # 關聯
    sender: Mapped["User"] = relationship(
        "User", foreign_keys=[sender_id], lazy="selectin"
    )
    recipient: Mapped["User"] = relationship(
        "User", foreign_keys=[recipient_id], lazy="selectin"
    )
    parent: Mapped[Optional["Message"]] = relationship(
        "Message", remote_side=[id], back_populates="replies", lazy="selectin"
    )
    replies: Mapped[List["Message"]] = relationship(
        "Message", back_populates="parent", lazy="selectin"
    )

    # 索引優化查詢
    __table_args__ = (
        Index('ix_messages_recipient_id_is_read', 'recipient_id', 'is_read'),
        Index('ix_messages_sender_id', 'sender_id'),
        Index('ix_messages_parent_id', 'parent_id'),
        Index('ix_messages_created_at', 'created_at'),
    )
