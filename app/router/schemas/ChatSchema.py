from datetime import datetime
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# === Request Schema ===

class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""
    message: str = Field(..., min_length=1, max_length=2000, description='User message')
    conversation_id: UUID | None = Field(None, description='Existing conversation ID, null to create new')

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
    actions_taken: list[ActionTakenItem] = []


class MessageItem(BaseModel):
    """A single message in a conversation."""
    role: str
    content: str | None = None
    created_at: datetime | None = None


class ConversationListItem(BaseModel):
    """Conversation list item."""
    id: UUID
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationListResponse(BaseModel):
    """Paginated conversation list response."""
    items: list[ConversationListItem]
    total: int
    page: int
    size: int


class ConversationDetailResponse(BaseModel):
    """Conversation detail with messages."""
    id: UUID
    title: str | None = None
    messages: list[MessageItem]
