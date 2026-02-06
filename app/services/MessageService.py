from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

from app.services.unitofwork.MessageUnitOfWork import (
    MessageUnitOfWork,
    MessageQueryUnitOfWork
)
from app.services.unitofwork.UserUnitOfWork import UserUnitOfWork
from app.domain.MessageModel import MessageModel
from app.exceptions.MessageException import (
    MessageNotFoundError,
    MessageAccessDeniedError,
    RecipientNotFoundError,
)

if TYPE_CHECKING:
    from app.router.schemas.MessageSchema import SendMessageRequest, ReplyMessageRequest


class MessageService:
    """Application service for message management operations."""

    def send_message(
        self,
        sender_id: str,
        request: SendMessageRequest
    ) -> MessageModel:
        """
        Send a new message.

        Args:
            sender_id: Sender's UUID
            request: Send message request

        Returns:
            The created message

        Raises:
            RecipientNotFoundError: If recipient does not exist
        """
        recipient_id = str(request.recipient_id)

        # Verify recipient exists
        with UserUnitOfWork() as user_uow:
            recipient = user_uow.repo.get_by_id(recipient_id)
            if not recipient:
                raise RecipientNotFoundError()

        # Create message
        message = MessageModel.create(
            subject=request.subject,
            content=request.content,
            sender_id=sender_id,
            recipient_id=recipient_id
        )

        with MessageUnitOfWork() as uow:
            saved_message = uow.repo.add(message)
            uow.commit()
            return saved_message

    def reply_message(
        self,
        user_id: str,
        message_id: int,
        request: ReplyMessageRequest
    ) -> MessageModel:
        """
        Reply to a message.

        Args:
            user_id: Replier's UUID
            message_id: Message ID to reply to
            request: Reply request

        Returns:
            The created reply message

        Raises:
            MessageNotFoundError: If original message does not exist
            MessageAccessDeniedError: If user cannot reply to this message
        """
        with MessageUnitOfWork() as uow:
            # Get original message
            original = uow.repo.get_by_id(message_id)
            if not original:
                raise MessageNotFoundError()

            # Check permission: only sender or recipient can reply
            if user_id != original.sender_id and user_id != original.recipient_id:
                raise MessageAccessDeniedError()

            # Determine reply recipient
            recipient_id = (
                original.sender_id
                if user_id == original.recipient_id
                else original.recipient_id
            )

            # Create reply
            reply = MessageModel.create(
                subject=f"Re: {original.subject}",
                content=request.content,
                sender_id=user_id,
                recipient_id=recipient_id,
                parent_id=message_id
            )

            saved_reply = uow.repo.add(reply)
            uow.commit()
            return saved_reply

    def get_inbox(
        self,
        user_id: str,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[MessageModel], int, int]:
        """
        Get user's inbox.

        Args:
            user_id: User's UUID
            page: Page number
            size: Page size

        Returns:
            (list of messages, total count, unread count)
        """
        with MessageQueryUnitOfWork() as uow:
            messages, total = uow.repo.get_inbox(user_id, page, size)
            unread_count = uow.repo.get_unread_count(user_id)

            # Add reply count
            for msg in messages:
                msg.reply_count = uow.repo.get_reply_count(msg.id)

            return messages, total, unread_count

    def get_sent(
        self,
        user_id: str,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[MessageModel], int]:
        """
        Get user's sent messages.

        Args:
            user_id: User's UUID
            page: Page number
            size: Page size

        Returns:
            (list of messages, total count)
        """
        with MessageQueryUnitOfWork() as uow:
            messages, total = uow.repo.get_sent(user_id, page, size)

            # Add reply count
            for msg in messages:
                msg.reply_count = uow.repo.get_reply_count(msg.id)

            return messages, total

    def get_message(self, user_id: str, message_id: int) -> MessageModel:
        """
        Get a single message detail.

        Args:
            user_id: User's UUID
            message_id: Message ID

        Returns:
            The message

        Raises:
            MessageNotFoundError: If message does not exist
            MessageAccessDeniedError: If user cannot view
        """
        with MessageQueryUnitOfWork() as uow:
            message = uow.repo.get_by_id(message_id)
            if not message:
                raise MessageNotFoundError()

            if not message.can_view(user_id):
                raise MessageAccessDeniedError()

            message.reply_count = uow.repo.get_reply_count(message_id)
            return message

    def get_thread(
        self,
        user_id: str,
        message_id: int
    ) -> Tuple[MessageModel, List[MessageModel]]:
        """
        Get a message thread.

        Args:
            user_id: User's UUID
            message_id: Original message ID

        Returns:
            (original message, list of replies)

        Raises:
            MessageNotFoundError: If message does not exist
            MessageAccessDeniedError: If user cannot view
        """
        with MessageQueryUnitOfWork() as uow:
            result = uow.repo.get_thread(message_id)
            if not result:
                raise MessageNotFoundError()

            original, replies = result

            # Check permission
            if not original.can_view(user_id):
                raise MessageAccessDeniedError()

            return original, replies

    def mark_as_read(self, user_id: str, message_id: int) -> None:
        """
        Mark a message as read.

        Args:
            user_id: User's UUID
            message_id: Message ID

        Raises:
            MessageNotFoundError: If message does not exist
            MessageAccessDeniedError: If user is not the recipient
        """
        with MessageUnitOfWork() as uow:
            message = uow.repo.get_by_id(message_id)
            if not message:
                raise MessageNotFoundError()

            # Only recipient can mark as read
            if user_id != message.recipient_id:
                raise MessageAccessDeniedError()

            if not message.is_read:
                uow.repo.mark_as_read(message_id)
                uow.commit()

    def batch_mark_as_read(self, user_id: str, message_ids: List[int]) -> int:
        """
        Batch mark messages as read.

        Args:
            user_id: User's UUID
            message_ids: List of message IDs

        Returns:
            Number of actually updated messages
        """
        with MessageUnitOfWork() as uow:
            count = uow.repo.batch_mark_as_read(message_ids, user_id)
            uow.commit()
            return count

    def delete_message(self, user_id: str, message_id: int) -> None:
        """
        Delete a message (soft delete).

        Args:
            user_id: User's UUID
            message_id: Message ID

        Raises:
            MessageNotFoundError: If message does not exist
            MessageAccessDeniedError: If user cannot delete
        """
        with MessageUnitOfWork() as uow:
            message = uow.repo.get_by_id(message_id)
            if not message:
                raise MessageNotFoundError()

            is_sender = user_id == message.sender_id
            is_recipient = user_id == message.recipient_id

            if not is_sender and not is_recipient:
                raise MessageAccessDeniedError()

            uow.repo.soft_delete(message_id, user_id, is_sender)
            uow.commit()

    def get_unread_count(self, user_id: str) -> int:
        """
        Get unread message count.

        Args:
            user_id: User's UUID

        Returns:
            Unread count
        """
        with MessageQueryUnitOfWork() as uow:
            return uow.repo.get_unread_count(user_id)
