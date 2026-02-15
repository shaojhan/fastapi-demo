from typing import Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime

from .BaseRepository import BaseRepository
from database.models.chat import Conversation, ChatMessage
from app.domain.ChatModel import ConversationModel, ChatMessageModel


class ChatRepository(BaseRepository):
    """Repository for Chat aggregate persistence operations."""

    def create_conversation(self, conversation: ConversationModel) -> ConversationModel:
        entity = Conversation(
            id=UUID(conversation.id),
            user_id=UUID(conversation.user_id),
            title=conversation.title,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return self._to_conversation_model(entity)

    def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        entity = self.db.query(Conversation).filter(
            Conversation.id == UUID(conversation_id)
        ).first()
        if not entity:
            return None
        return self._to_conversation_model(entity)

    def get_conversations_by_user(
        self, user_id: str, page: int = 1, size: int = 20
    ) -> Tuple[List[ConversationModel], int]:
        query = self.db.query(Conversation).filter(
            Conversation.user_id == UUID(user_id)
        )
        total = query.count()
        conversations = query.order_by(
            Conversation.updated_at.desc().nullslast(),
            Conversation.created_at.desc()
        ).offset((page - 1) * size).limit(size).all()
        return [self._to_conversation_model(c) for c in conversations], total

    def update_conversation_title(self, conversation_id: str, title: str) -> None:
        entity = self.db.query(Conversation).filter(
            Conversation.id == UUID(conversation_id)
        ).first()
        if entity:
            entity.title = title[:255] if title else None
            self.db.flush()

    def delete_conversation(self, conversation_id: str) -> bool:
        entity = self.db.query(Conversation).filter(
            Conversation.id == UUID(conversation_id)
        ).first()
        if not entity:
            return False
        self.db.delete(entity)
        self.db.flush()
        return True

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_call_id: str | None = None,
    ) -> ChatMessageModel:
        entity = ChatMessage(
            id=uuid4(),
            conversation_id=UUID(conversation_id),
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return self._to_message_model(entity)

    def get_messages(
        self, conversation_id: str, limit: int = 50
    ) -> List[ChatMessageModel]:
        entities = self.db.query(ChatMessage).filter(
            ChatMessage.conversation_id == UUID(conversation_id)
        ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
        return [self._to_message_model(e) for e in entities]

    def _to_conversation_model(self, entity: Conversation) -> ConversationModel:
        return ConversationModel(
            id=str(entity.id),
            user_id=str(entity.user_id),
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_message_model(self, entity: ChatMessage) -> ChatMessageModel:
        return ChatMessageModel(
            id=str(entity.id),
            conversation_id=str(entity.conversation_id),
            role=entity.role,
            content=entity.content,
            tool_calls=entity.tool_calls,
            tool_call_id=entity.tool_call_id,
            created_at=entity.created_at,
        )
