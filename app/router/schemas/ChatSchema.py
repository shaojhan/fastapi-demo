from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# === Request Schema ===

class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""
    message: str = Field(..., min_length=1, max_length=2000, description='User message')
    conversation_id: Optional[UUID] = Field(None, description='Existing conversation ID, null to create new')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'message': '幫我明天下午2點到3點安排一個會議，標題是團隊週會',
                    'conversation_id': None,
                }
            ]
        }
    }


# === Response Schema ===

class ActionTakenItem(BaseModel):
    """Action taken by the AI agent."""
    tool: str
    args: dict
    success: bool = True


class ChatResponse(BaseModel):
    """Response from the AI chat."""
    conversation_id: UUID
    message: str
    actions_taken: List[ActionTakenItem] = []


class MessageItem(BaseModel):
    """A single message in a conversation."""
    role: str
    content: Optional[str] = None
    created_at: Optional[datetime] = None


class ConversationListItem(BaseModel):
    """Conversation list item."""
    id: UUID
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    """Paginated conversation list response."""
    items: List[ConversationListItem]
    total: int
    page: int
    size: int


class ConversationDetailResponse(BaseModel):
    """Conversation detail with messages."""
    id: UUID
    title: Optional[str] = None
    messages: List[MessageItem]
