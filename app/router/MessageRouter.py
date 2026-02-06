from fastapi import APIRouter, Depends, Query
from typing import List
from uuid import UUID

from app.router.schemas.MessageSchema import (
    SendMessageRequest,
    ReplyMessageRequest,
    BatchMarkReadRequest,
    MessageResponse,
    MessageListItem,
    MessageListResponse,
    MessageThreadResponse,
    UnreadCountResponse,
    MessageActionResponse,
    MessageParticipantResponse,
)
from app.services.MessageService import MessageService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import get_current_user


router = APIRouter(prefix='/messages', tags=['message'])


def get_message_service() -> MessageService:
    return MessageService()


def _to_participant_response(participant) -> MessageParticipantResponse:
    """Convert participant to response format."""
    return MessageParticipantResponse(
        user_id=UUID(participant.user_id),
        username=participant.username,
        email=participant.email
    )


def _to_message_response(message, reply_count: int = 0) -> MessageResponse:
    """Convert message to response format."""
    return MessageResponse(
        id=message.id,
        subject=message.subject,
        content=message.content,
        sender=_to_participant_response(message.sender),
        recipient=_to_participant_response(message.recipient),
        parent_id=message.parent_id,
        is_read=message.is_read,
        read_at=message.read_at,
        created_at=message.created_at,
        reply_count=reply_count
    )


def _to_list_item(message) -> MessageListItem:
    """Convert message to list item format."""
    content_preview = message.content[:100] + '...' if len(message.content) > 100 else message.content
    return MessageListItem(
        id=message.id,
        subject=message.subject,
        content_preview=content_preview,
        sender=_to_participant_response(message.sender),
        recipient=_to_participant_response(message.recipient),
        is_read=message.is_read,
        created_at=message.created_at,
        reply_count=message.reply_count
    )


@router.post('/', response_model=MessageResponse, operation_id='send_message')
async def send_message(
    request_body: SendMessageRequest,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """Send a new message."""
    message = service.send_message(
        sender_id=current_user.id,
        request=request_body
    )
    return _to_message_response(message, 0)


@router.post('/{message_id}/reply', response_model=MessageResponse, operation_id='reply_message')
async def reply_message(
    message_id: int,
    request_body: ReplyMessageRequest,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """Reply to a message."""
    reply = service.reply_message(
        user_id=current_user.id,
        message_id=message_id,
        request=request_body
    )
    return _to_message_response(reply, 0)


@router.get('/inbox', response_model=MessageListResponse, operation_id='get_inbox')
async def get_inbox(
    page: int = Query(1, ge=1, description='Page number'),
    size: int = Query(20, ge=1, le=100, description='Page size'),
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageListResponse:
    """Get inbox messages."""
    messages, total, unread_count = service.get_inbox(
        user_id=current_user.id,
        page=page,
        size=size
    )
    items = [_to_list_item(m) for m in messages]
    return MessageListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        unread_count=unread_count
    )


@router.get('/sent', response_model=MessageListResponse, operation_id='get_sent')
async def get_sent(
    page: int = Query(1, ge=1, description='Page number'),
    size: int = Query(20, ge=1, le=100, description='Page size'),
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageListResponse:
    """Get sent messages."""
    messages, total = service.get_sent(
        user_id=current_user.id,
        page=page,
        size=size
    )
    items = [_to_list_item(m) for m in messages]
    return MessageListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        unread_count=0
    )


@router.get('/unread-count', response_model=UnreadCountResponse, operation_id='get_unread_count')
async def get_unread_count(
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> UnreadCountResponse:
    """Get unread message count."""
    count = service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.get('/thread/{message_id}', response_model=MessageThreadResponse, operation_id='get_thread')
async def get_thread(
    message_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageThreadResponse:
    """Get message thread with all replies."""
    original, replies = service.get_thread(
        user_id=current_user.id,
        message_id=message_id
    )
    return MessageThreadResponse(
        original_message=_to_message_response(original, len(replies)),
        replies=[_to_message_response(r, 0) for r in replies],
        total_messages=1 + len(replies)
    )


@router.get('/{message_id}', response_model=MessageResponse, operation_id='get_message')
async def get_message(
    message_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """Get a single message detail."""
    message = service.get_message(
        user_id=current_user.id,
        message_id=message_id
    )
    return _to_message_response(message, message.reply_count)


@router.put('/{message_id}/read', response_model=MessageActionResponse, operation_id='mark_as_read')
async def mark_as_read(
    message_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageActionResponse:
    """Mark a message as read."""
    service.mark_as_read(
        user_id=current_user.id,
        message_id=message_id
    )
    return MessageActionResponse(message='Message marked as read.')


@router.put('/batch-read', response_model=MessageActionResponse, operation_id='batch_mark_as_read')
async def batch_mark_as_read(
    request_body: BatchMarkReadRequest,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageActionResponse:
    """Batch mark messages as read."""
    count = service.batch_mark_as_read(
        user_id=current_user.id,
        message_ids=request_body.message_ids
    )
    return MessageActionResponse(message=f'{count} messages marked as read.')


@router.delete('/{message_id}', response_model=MessageActionResponse, operation_id='delete_message')
async def delete_message(
    message_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: MessageService = Depends(get_message_service)
) -> MessageActionResponse:
    """Delete a message (soft delete)."""
    service.delete_message(
        user_id=current_user.id,
        message_id=message_id
    )
    return MessageActionResponse(message='Message deleted.')
