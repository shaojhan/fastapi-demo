from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from .BaseRepository import BaseRepository
from database.models.message import Message
from app.domain.MessageModel import MessageModel, MessageParticipant


class MessageRepository(BaseRepository):
    """Repository for Message aggregate persistence operations."""

    def add(self, message_model: MessageModel) -> MessageModel:
        """
        Add a new message to the database.

        Args:
            message_model: The message domain model

        Returns:
            The created message with ID
        """
        message_entity = Message(
            subject=message_model.subject,
            content=message_model.content,
            sender_id=UUID(message_model.sender_id),
            recipient_id=UUID(message_model.recipient_id),
            parent_id=message_model.parent_id,
            is_read=message_model.is_read,
            read_at=message_model.read_at,
            deleted_by_sender=message_model.deleted_by_sender,
            deleted_by_recipient=message_model.deleted_by_recipient,
        )

        self.db.add(message_entity)
        self.db.flush()
        self.db.refresh(message_entity)

        return self._to_domain_model(message_entity)

    def get_by_id(self, message_id: int) -> Optional[MessageModel]:
        """
        Get a message by ID.

        Args:
            message_id: The message ID

        Returns:
            MessageModel if found, None otherwise
        """
        message_entity = self.db.query(Message).filter(
            Message.id == message_id
        ).first()

        if not message_entity:
            return None

        return self._to_domain_model(message_entity)

    def get_inbox(
        self,
        user_id: str,
        page: int,
        size: int
    ) -> Tuple[List[MessageModel], int]:
        """
        Get user's inbox messages (paginated).

        Args:
            user_id: User's UUID
            page: Page number
            size: Page size

        Returns:
            (list of messages, total count)
        """
        query = self.db.query(Message).filter(
            Message.recipient_id == UUID(user_id),
            Message.deleted_by_recipient == False,
            Message.parent_id == None  # Only show original messages, not replies
        )

        total = query.count()
        messages = query.order_by(
            Message.is_read.asc(),  # Unread first
            Message.created_at.desc()
        ).offset((page - 1) * size).limit(size).all()

        return [self._to_domain_model(m) for m in messages], total

    def get_sent(
        self,
        user_id: str,
        page: int,
        size: int
    ) -> Tuple[List[MessageModel], int]:
        """
        Get user's sent messages (paginated).

        Args:
            user_id: User's UUID
            page: Page number
            size: Page size

        Returns:
            (list of messages, total count)
        """
        query = self.db.query(Message).filter(
            Message.sender_id == UUID(user_id),
            Message.deleted_by_sender == False,
            Message.parent_id == None  # Only show original messages
        )

        total = query.count()
        messages = query.order_by(
            Message.created_at.desc()
        ).offset((page - 1) * size).limit(size).all()

        return [self._to_domain_model(m) for m in messages], total

    def get_thread(self, message_id: int) -> Optional[Tuple[MessageModel, List[MessageModel]]]:
        """
        Get a message thread (original message and all replies).

        Args:
            message_id: The original message ID

        Returns:
            (original message, list of replies) or None
        """
        original = self.db.query(Message).filter(
            Message.id == message_id
        ).first()

        if not original:
            return None

        replies = self.db.query(Message).filter(
            Message.parent_id == message_id
        ).order_by(Message.created_at.asc()).all()

        return (
            self._to_domain_model(original),
            [self._to_domain_model(r) for r in replies]
        )

    def get_unread_count(self, user_id: str) -> int:
        """
        Get the count of unread messages for a user.

        Args:
            user_id: User's UUID

        Returns:
            Unread message count
        """
        return self.db.query(Message).filter(
            Message.recipient_id == UUID(user_id),
            Message.is_read == False,
            Message.deleted_by_recipient == False
        ).count()

    def get_reply_count(self, message_id: int) -> int:
        """
        Get the count of replies for a message.

        Args:
            message_id: The message ID

        Returns:
            Reply count
        """
        return self.db.query(Message).filter(
            Message.parent_id == message_id
        ).count()

    def mark_as_read(self, message_id: int) -> bool:
        """
        Mark a message as read.

        Args:
            message_id: The message ID

        Returns:
            True if successful
        """
        message = self.db.query(Message).filter(
            Message.id == message_id
        ).first()

        if not message:
            return False

        message.is_read = True
        message.read_at = datetime.now()
        self.db.flush()
        return True

    def batch_mark_as_read(self, message_ids: List[int], user_id: str) -> int:
        """
        Batch mark messages as read.

        Args:
            message_ids: List of message IDs
            user_id: User's UUID (ensure only marking own messages)

        Returns:
            Number of updated messages
        """
        result = self.db.query(Message).filter(
            Message.id.in_(message_ids),
            Message.recipient_id == UUID(user_id),
            Message.is_read == False
        ).update({
            Message.is_read: True,
            Message.read_at: datetime.now()
        }, synchronize_session=False)

        self.db.flush()
        return result

    def soft_delete(self, message_id: int, user_id: str, is_sender: bool) -> bool:
        """
        Soft delete a message.

        Args:
            message_id: The message ID
            user_id: User's UUID
            is_sender: True if deleting as sender

        Returns:
            True if successful
        """
        message = self.db.query(Message).filter(
            Message.id == message_id
        ).first()

        if not message:
            return False

        if is_sender:
            message.deleted_by_sender = True
        else:
            message.deleted_by_recipient = True

        self.db.flush()
        return True

    def _to_domain_model(self, entity: Message) -> MessageModel:
        """
        Convert a Message ORM entity to a MessageModel domain object.

        Args:
            entity: The Message ORM entity

        Returns:
            A MessageModel domain object
        """
        sender = None
        recipient = None

        if entity.sender:
            sender = MessageParticipant(
                user_id=str(entity.sender.id),
                username=entity.sender.uid,
                email=entity.sender.email
            )

        if entity.recipient:
            recipient = MessageParticipant(
                user_id=str(entity.recipient.id),
                username=entity.recipient.uid,
                email=entity.recipient.email
            )

        return MessageModel.reconstitute(
            id=entity.id,
            subject=entity.subject,
            content=entity.content,
            sender_id=str(entity.sender_id),
            recipient_id=str(entity.recipient_id),
            is_read=entity.is_read,
            read_at=entity.read_at,
            parent_id=entity.parent_id,
            deleted_by_sender=entity.deleted_by_sender,
            deleted_by_recipient=entity.deleted_by_recipient,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            sender=sender,
            recipient=recipient
        )


class MessageQueryRepository(BaseRepository):
    """Query repository for read-only message operations."""

    def exists_by_id(self, message_id: int) -> bool:
        """Check if a message exists."""
        return self.db.query(Message).filter(
            Message.id == message_id
        ).first() is not None

    def _to_domain_model(self, entity: Message) -> MessageModel:
        """Convert ORM entity to domain model."""
        sender = None
        recipient = None

        if entity.sender:
            sender = MessageParticipant(
                user_id=str(entity.sender.id),
                username=entity.sender.uid,
                email=entity.sender.email
            )

        if entity.recipient:
            recipient = MessageParticipant(
                user_id=str(entity.recipient.id),
                username=entity.recipient.uid,
                email=entity.recipient.email
            )

        return MessageModel.reconstitute(
            id=entity.id,
            subject=entity.subject,
            content=entity.content,
            sender_id=str(entity.sender_id),
            recipient_id=str(entity.recipient_id),
            is_read=entity.is_read,
            read_at=entity.read_at,
            parent_id=entity.parent_id,
            deleted_by_sender=entity.deleted_by_sender,
            deleted_by_recipient=entity.deleted_by_recipient,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            sender=sender,
            recipient=recipient
        )
