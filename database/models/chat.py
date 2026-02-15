from app.db import Base

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Uuid,
    String,
    Text,
    DateTime,
    JSON,
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


class Conversation(Base):
    """
    對話 ORM 模型
    儲存使用者與 AI 排程助手的對話
    """
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    # 對話擁有者
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 對話標題（從首條訊息自動生成）
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 關聯
    user: Mapped["User"] = relationship("User", lazy="selectin")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="conversation",
        cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )

    __table_args__ = (
        Index('ix_conversations_user_id', 'user_id'),
    )


class ChatMessage(Base):
    """
    對話訊息 ORM 模型
    儲存對話中的每條訊息（user / assistant / tool）
    """
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 所屬對話
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )

    # 訊息內容
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | tool
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 關聯
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index('ix_chat_messages_conversation_id', 'conversation_id'),
    )
