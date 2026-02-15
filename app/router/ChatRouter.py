from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_employee
from app.router.schemas.ChatSchema import (
    ChatRequest,
    ChatResponse,
    ConversationListResponse,
    ConversationListItem,
    ConversationDetailResponse,
    MessageItem,
)
from app.services.ScheduleAgentService import ScheduleAgentService

router = APIRouter(prefix='/chat', tags=['chat'])


def get_agent_service() -> ScheduleAgentService:
    return ScheduleAgentService()


@router.post('/', response_model=ChatResponse)
async def send_message(
    request_body: ChatRequest,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleAgentService = Depends(get_agent_service),
) -> ChatResponse:
    """Send a message to the AI schedule assistant."""
    result = await service.chat(
        user_id=current_user.id,
        username=current_user.uid,
        message=request_body.message,
        conversation_id=str(request_body.conversation_id) if request_body.conversation_id else None,
    )
    return ChatResponse(
        conversation_id=UUID(result["conversation_id"]),
        message=result["message"],
        actions_taken=result["actions_taken"],
    )


@router.get('/conversations', response_model=ConversationListResponse)
def list_conversations(
    page: int = Query(1, ge=1, description='Page number'),
    size: int = Query(20, ge=1, le=100, description='Page size'),
    current_user: UserModel = Depends(require_employee),
    service: ScheduleAgentService = Depends(get_agent_service),
) -> ConversationListResponse:
    """List user's conversations."""
    conversations, total = service.get_conversations(current_user.id, page, size)
    return ConversationListResponse(
        items=[
            ConversationListItem(
                id=UUID(c.id),
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get('/conversations/{conversation_id}', response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: UUID,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleAgentService = Depends(get_agent_service),
) -> ConversationDetailResponse:
    """Get conversation detail with messages."""
    messages = service.get_conversation_messages(current_user.id, str(conversation_id))
    return ConversationDetailResponse(
        id=conversation_id,
        messages=[
            MessageItem(
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"],
            )
            for m in messages
        ],
    )


@router.delete('/conversations/{conversation_id}')
def delete_conversation(
    conversation_id: UUID,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleAgentService = Depends(get_agent_service),
) -> dict:
    """Delete a conversation."""
    service.delete_conversation(current_user.id, str(conversation_id))
    return {"message": "Conversation deleted", "success": True}
