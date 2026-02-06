from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class MessageParticipant:
    """
    Value Object representing a message participant's info.
    """
    user_id: str
    username: str
    email: str


class MessageModel:
    """
    Aggregate Root representing a message in the domain.
    Use factory methods `create` or `reconstitute` to create instances.
    """

    def __init__(
        self,
        id: int | None,
        subject: str,
        content: str,
        sender_id: str,
        recipient_id: str,
        parent_id: int | None = None,
        is_read: bool = False,
        read_at: datetime | None = None,
        deleted_by_sender: bool = False,
        deleted_by_recipient: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        sender: MessageParticipant | None = None,
        recipient: MessageParticipant | None = None,
        reply_count: int = 0
    ):
        self._id = id
        self._subject = subject
        self._content = content
        self._sender_id = sender_id
        self._recipient_id = recipient_id
        self._parent_id = parent_id
        self._is_read = is_read
        self._read_at = read_at
        self._deleted_by_sender = deleted_by_sender
        self._deleted_by_recipient = deleted_by_recipient
        self._created_at = created_at
        self._updated_at = updated_at
        self._sender = sender
        self._recipient = recipient
        self._reply_count = reply_count

    # Properties
    @property
    def id(self) -> int | None:
        return self._id

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def content(self) -> str:
        return self._content

    @property
    def sender_id(self) -> str:
        return self._sender_id

    @property
    def recipient_id(self) -> str:
        return self._recipient_id

    @property
    def parent_id(self) -> int | None:
        return self._parent_id

    @property
    def is_read(self) -> bool:
        return self._is_read

    @property
    def read_at(self) -> datetime | None:
        return self._read_at

    @property
    def deleted_by_sender(self) -> bool:
        return self._deleted_by_sender

    @property
    def deleted_by_recipient(self) -> bool:
        return self._deleted_by_recipient

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def sender(self) -> MessageParticipant | None:
        return self._sender

    @property
    def recipient(self) -> MessageParticipant | None:
        return self._recipient

    @property
    def reply_count(self) -> int:
        return self._reply_count

    @reply_count.setter
    def reply_count(self, value: int) -> None:
        self._reply_count = value

    # Factory methods
    @staticmethod
    def create(
        subject: str,
        content: str,
        sender_id: str,
        recipient_id: str,
        parent_id: int | None = None
    ) -> "MessageModel":
        """
        Factory method to create a new message.

        Args:
            subject: Message subject
            content: Message content
            sender_id: Sender's UUID
            recipient_id: Recipient's UUID
            parent_id: Parent message ID (for replies)

        Returns:
            A new MessageModel instance

        Raises:
            ValueError: If subject or content is empty, or sending to self
        """
        if not subject or not subject.strip():
            raise ValueError("Subject cannot be empty")
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        if sender_id == recipient_id:
            raise ValueError("Cannot send message to yourself")

        return MessageModel(
            id=None,
            subject=subject.strip(),
            content=content.strip(),
            sender_id=sender_id,
            recipient_id=recipient_id,
            parent_id=parent_id,
            is_read=False,
            read_at=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )

    @staticmethod
    def reconstitute(
        id: int,
        subject: str,
        content: str,
        sender_id: str,
        recipient_id: str,
        is_read: bool,
        read_at: datetime | None,
        parent_id: int | None,
        deleted_by_sender: bool,
        deleted_by_recipient: bool,
        created_at: datetime | None,
        updated_at: datetime | None,
        sender: MessageParticipant | None = None,
        recipient: MessageParticipant | None = None,
        reply_count: int = 0
    ) -> "MessageModel":
        """
        Factory method to reconstitute a message from persistence.

        Args:
            id: Message ID
            subject: Message subject
            content: Message content
            sender_id: Sender's UUID
            recipient_id: Recipient's UUID
            is_read: Whether the message has been read
            read_at: When the message was read
            parent_id: Parent message ID
            deleted_by_sender: Whether deleted by sender
            deleted_by_recipient: Whether deleted by recipient
            created_at: Creation timestamp
            updated_at: Last update timestamp
            sender: Sender participant info
            recipient: Recipient participant info
            reply_count: Number of replies

        Returns:
            A reconstituted MessageModel instance
        """
        return MessageModel(
            id=id,
            subject=subject,
            content=content,
            sender_id=sender_id,
            recipient_id=recipient_id,
            parent_id=parent_id,
            is_read=is_read,
            read_at=read_at,
            deleted_by_sender=deleted_by_sender,
            deleted_by_recipient=deleted_by_recipient,
            created_at=created_at,
            updated_at=updated_at,
            sender=sender,
            recipient=recipient,
            reply_count=reply_count
        )

    # Business methods
    def mark_as_read(self) -> None:
        """
        Mark this message as read.

        Raises:
            ValueError: If already read
        """
        if self._is_read:
            raise ValueError("Message is already read")
        self._is_read = True
        self._read_at = datetime.now()
        self._updated_at = datetime.now()

    def delete_for_sender(self) -> None:
        """Mark as deleted by sender."""
        self._deleted_by_sender = True
        self._updated_at = datetime.now()

    def delete_for_recipient(self) -> None:
        """Mark as deleted by recipient."""
        self._deleted_by_recipient = True
        self._updated_at = datetime.now()

    def is_reply(self) -> bool:
        """Check if this is a reply message."""
        return self._parent_id is not None

    def can_view(self, user_id: str) -> bool:
        """
        Check if a user can view this message.

        Args:
            user_id: The user ID to check

        Returns:
            True if the user can view
        """
        if user_id == self._sender_id and not self._deleted_by_sender:
            return True
        if user_id == self._recipient_id and not self._deleted_by_recipient:
            return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MessageModel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
