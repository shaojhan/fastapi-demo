from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# === Request Schema ===

class SendMessageRequest(BaseModel):
    """Request schema for sending a message."""
    recipient_id: UUID = Field(..., description='Recipient UUID')
    subject: str = Field(..., min_length=1, max_length=255, description='Subject')
    content: str = Field(..., min_length=1, description='Content')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'recipient_id': '11d200ac-48d8-4675-bfc0-a3a61af3c499',
                    'subject': 'Meeting Notice',
                    'content': 'There is a department meeting at 3pm tomorrow, please attend on time.'
                }
            ]
        }
    }


class ReplyMessageRequest(BaseModel):
    """Request schema for replying to a message."""
    content: str = Field(..., min_length=1, description='Reply content')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'content': 'Got it, I will be there on time.'
                }
            ]
        }
    }


class BatchMarkReadRequest(BaseModel):
    """Request schema for batch marking messages as read."""
    message_ids: List[int] = Field(..., min_length=1, description='List of message IDs')


# === Response Schema ===

class MessageParticipantResponse(BaseModel):
    """Message participant info."""
    user_id: UUID
    username: str
    email: str


class MessageResponse(BaseModel):
    """Single message response."""
    id: int
    subject: str
    content: str
    sender: MessageParticipantResponse
    recipient: MessageParticipantResponse
    parent_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    reply_count: int = 0


class MessageListItem(BaseModel):
    """Message list item."""
    id: int
    subject: str
    content_preview: str = Field(description='Content preview (first 100 chars)')
    sender: MessageParticipantResponse
    recipient: MessageParticipantResponse
    is_read: bool
    created_at: datetime
    reply_count: int = 0


class MessageListResponse(BaseModel):
    """Paginated message list response."""
    items: List[MessageListItem]
    total: int
    page: int
    size: int
    unread_count: int = 0


class MessageThreadResponse(BaseModel):
    """Message thread response."""
    original_message: MessageResponse
    replies: List[MessageResponse]
    total_messages: int


class UnreadCountResponse(BaseModel):
    """Unread message count response."""
    count: int


class MessageActionResponse(BaseModel):
    """Action result response."""
    message: str
    success: bool = True
