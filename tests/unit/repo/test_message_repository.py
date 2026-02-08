"""
Unit tests for MessageRepository.
Tests the data access layer for Message aggregates.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.MessageRepository import (
    MessageRepository,
    MessageQueryRepository
)
from app.domain.MessageModel import MessageModel
from database.models.message import Message


class TestMessageRepository:
    """Test suite for MessageRepository CRUD operations."""

    def test_add_message(self, test_db_session: Session, sample_users):
        """Test adding a new message."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[0]
        recipient = sample_users[1]

        # Create message using domain factory
        message = MessageModel.create(
            subject="Test Subject",
            content="Test content",
            sender_id=str(sender.id),
            recipient_id=str(recipient.id)
        )

        # Add to repository
        created_message = repo.add(message)

        # Verify
        assert created_message.id is not None
        assert created_message.subject == "Test Subject"
        assert created_message.content == "Test content"
        assert created_message.sender_id == str(sender.id)
        assert created_message.recipient_id == str(recipient.id)
        assert created_message.is_read is False
        assert created_message.created_at is not None

    def test_add_reply_message(self, test_db_session: Session, sample_users, sample_messages):
        """Test adding a reply message."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[1]  # Reply from recipient
        recipient = sample_users[0]  # To original sender
        original_message = sample_messages[0]

        reply = MessageModel.create(
            subject=f"Re: {original_message.subject}",
            content="Reply content",
            sender_id=str(sender.id),
            recipient_id=str(recipient.id),
            parent_id=original_message.id
        )

        created_reply = repo.add(reply)

        assert created_reply.parent_id == original_message.id
        assert created_reply.subject == f"Re: {original_message.subject}"

    def test_get_by_id_existing(self, test_db_session: Session, sample_messages):
        """Test retrieving a message by ID."""
        repo = MessageRepository(test_db_session)
        existing_message = sample_messages[0]

        # Retrieve by ID
        retrieved = repo.get_by_id(existing_message.id)

        # Verify
        assert retrieved is not None
        assert retrieved.id == existing_message.id
        assert retrieved.subject == "Hello"
        assert retrieved.sender is not None
        assert retrieved.recipient is not None

    def test_get_by_id_non_existing(self, test_db_session: Session):
        """Test retrieving a non-existing message by ID."""
        repo = MessageRepository(test_db_session)

        retrieved = repo.get_by_id(999999)

        assert retrieved is None

    def test_get_inbox(self, test_db_session: Session, sample_users, sample_messages):
        """Test retrieving user inbox."""
        repo = MessageRepository(test_db_session)
        recipient = sample_users[1]

        # Get inbox
        messages, total = repo.get_inbox(str(recipient.id), page=1, size=20)

        # Both messages are sent to user2
        assert total == 2
        assert len(messages) == 2
        # Unread first, then by created_at desc
        for msg in messages:
            assert msg.recipient_id == str(recipient.id)

    def test_get_inbox_excludes_deleted(self, test_db_session: Session, sample_users):
        """Test inbox excludes deleted messages."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[0]
        recipient = sample_users[1]

        # Create a message marked as deleted by recipient
        deleted_message = Message(
            subject="Deleted Message",
            content="This was deleted",
            sender_id=sender.id,
            recipient_id=recipient.id,
            deleted_by_recipient=True
        )
        test_db_session.add(deleted_message)
        test_db_session.commit()

        messages, total = repo.get_inbox(str(recipient.id), page=1, size=20)

        # Should not include deleted message
        for msg in messages:
            assert msg.subject != "Deleted Message"

    def test_get_inbox_excludes_replies(self, test_db_session: Session, sample_users, sample_messages):
        """Test inbox excludes reply messages (only original messages)."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[1]
        recipient = sample_users[0]
        original = sample_messages[0]

        # Create a reply
        reply = Message(
            subject="Re: Hello",
            content="Reply content",
            sender_id=sender.id,
            recipient_id=recipient.id,
            parent_id=original.id
        )
        test_db_session.add(reply)
        test_db_session.commit()

        # Get inbox for user1 (recipient of the reply)
        messages, total = repo.get_inbox(str(recipient.id), page=1, size=20)

        # Should not include replies
        for msg in messages:
            assert msg.parent_id is None

    def test_get_sent(self, test_db_session: Session, sample_users, sample_messages):
        """Test retrieving sent messages."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[0]

        messages, total = repo.get_sent(str(sender.id), page=1, size=20)

        assert total == 2
        assert len(messages) == 2
        for msg in messages:
            assert msg.sender_id == str(sender.id)

    def test_get_sent_excludes_deleted(self, test_db_session: Session, sample_users):
        """Test sent messages excludes those deleted by sender."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[0]
        recipient = sample_users[1]

        # Create a message marked as deleted by sender
        deleted_message = Message(
            subject="Deleted by Sender",
            content="Content",
            sender_id=sender.id,
            recipient_id=recipient.id,
            deleted_by_sender=True
        )
        test_db_session.add(deleted_message)
        test_db_session.commit()

        messages, total = repo.get_sent(str(sender.id), page=1, size=20)

        for msg in messages:
            assert msg.subject != "Deleted by Sender"

    def test_get_thread(self, test_db_session: Session, sample_users, sample_messages):
        """Test retrieving a message thread."""
        repo = MessageRepository(test_db_session)
        original = sample_messages[0]
        sender = sample_users[1]
        recipient = sample_users[0]

        # Create replies
        reply1 = Message(
            subject="Re: Hello",
            content="First reply",
            sender_id=sender.id,
            recipient_id=recipient.id,
            parent_id=original.id
        )
        reply2 = Message(
            subject="Re: Hello",
            content="Second reply",
            sender_id=recipient.id,
            recipient_id=sender.id,
            parent_id=original.id
        )
        test_db_session.add(reply1)
        test_db_session.add(reply2)
        test_db_session.commit()

        # Get thread
        result = repo.get_thread(original.id)

        assert result is not None
        original_msg, replies = result
        assert original_msg.id == original.id
        assert len(replies) == 2

    def test_get_thread_non_existing(self, test_db_session: Session):
        """Test retrieving non-existing thread."""
        repo = MessageRepository(test_db_session)

        result = repo.get_thread(999999)

        assert result is None

    def test_get_unread_count(self, test_db_session: Session, sample_users, sample_messages):
        """Test getting unread message count."""
        repo = MessageRepository(test_db_session)
        recipient = sample_users[1]

        # One of the sample messages is unread
        count = repo.get_unread_count(str(recipient.id))

        assert count == 1

    def test_get_reply_count(self, test_db_session: Session, sample_users, sample_messages):
        """Test getting reply count for a message."""
        repo = MessageRepository(test_db_session)
        original = sample_messages[0]
        sender = sample_users[1]
        recipient = sample_users[0]

        # Create 3 replies
        for i in range(3):
            reply = Message(
                subject=f"Re: Hello {i}",
                content=f"Reply {i}",
                sender_id=sender.id,
                recipient_id=recipient.id,
                parent_id=original.id
            )
            test_db_session.add(reply)
        test_db_session.commit()

        count = repo.get_reply_count(original.id)

        assert count == 3

    def test_mark_as_read(self, test_db_session: Session, sample_messages):
        """Test marking a message as read."""
        repo = MessageRepository(test_db_session)
        unread_message = sample_messages[0]  # First message is unread

        result = repo.mark_as_read(unread_message.id)

        assert result is True
        retrieved = repo.get_by_id(unread_message.id)
        assert retrieved.is_read is True
        assert retrieved.read_at is not None

    def test_mark_as_read_non_existing(self, test_db_session: Session):
        """Test marking non-existing message as read."""
        repo = MessageRepository(test_db_session)

        result = repo.mark_as_read(999999)

        assert result is False

    def test_batch_mark_as_read(self, test_db_session: Session, sample_users):
        """Test batch marking messages as read."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[0]
        recipient = sample_users[1]

        # Create multiple unread messages
        message_ids = []
        for i in range(3):
            msg = Message(
                subject=f"Batch Test {i}",
                content=f"Content {i}",
                sender_id=sender.id,
                recipient_id=recipient.id,
                is_read=False
            )
            test_db_session.add(msg)
            test_db_session.flush()
            message_ids.append(msg.id)
        test_db_session.commit()

        # Batch mark as read
        count = repo.batch_mark_as_read(message_ids, str(recipient.id))

        assert count == 3
        for msg_id in message_ids:
            msg = repo.get_by_id(msg_id)
            assert msg.is_read is True

    def test_batch_mark_as_read_only_own_messages(self, test_db_session: Session, sample_users):
        """Test batch mark only marks user's own received messages."""
        repo = MessageRepository(test_db_session)
        sender = sample_users[0]
        recipient = sample_users[1]
        other_user = sample_users[2]

        # Create message for recipient
        msg = Message(
            subject="For Recipient",
            content="Content",
            sender_id=sender.id,
            recipient_id=recipient.id,
            is_read=False
        )
        test_db_session.add(msg)
        test_db_session.flush()
        test_db_session.commit()

        # Try to mark as read by other user (should not update)
        count = repo.batch_mark_as_read([msg.id], str(other_user.id))

        assert count == 0

    def test_soft_delete_as_sender(self, test_db_session: Session, sample_messages, sample_users):
        """Test soft deleting a message as sender."""
        repo = MessageRepository(test_db_session)
        message = sample_messages[0]
        sender = sample_users[0]

        result = repo.soft_delete(message.id, str(sender.id), is_sender=True)

        assert result is True
        # Message should still be retrievable
        retrieved = repo.get_by_id(message.id)
        assert retrieved is not None
        assert retrieved.deleted_by_sender is True
        assert retrieved.deleted_by_recipient is False

    def test_soft_delete_as_recipient(self, test_db_session: Session, sample_messages, sample_users):
        """Test soft deleting a message as recipient."""
        repo = MessageRepository(test_db_session)
        message = sample_messages[0]
        recipient = sample_users[1]

        result = repo.soft_delete(message.id, str(recipient.id), is_sender=False)

        assert result is True
        retrieved = repo.get_by_id(message.id)
        assert retrieved is not None
        assert retrieved.deleted_by_sender is False
        assert retrieved.deleted_by_recipient is True

    def test_soft_delete_non_existing(self, test_db_session: Session, sample_users):
        """Test soft deleting non-existing message."""
        repo = MessageRepository(test_db_session)

        result = repo.soft_delete(999999, str(sample_users[0].id), is_sender=True)

        assert result is False

    def test_domain_model_preserves_participant_info(self, test_db_session: Session, sample_messages):
        """Test that converting to domain model preserves participant info."""
        repo = MessageRepository(test_db_session)
        message = sample_messages[0]

        retrieved = repo.get_by_id(message.id)

        # Sender info
        assert retrieved.sender is not None
        assert retrieved.sender.user_id == str(message.sender_id)
        assert retrieved.sender.username == "user1"
        assert retrieved.sender.email == "user1@example.com"

        # Recipient info
        assert retrieved.recipient is not None
        assert retrieved.recipient.user_id == str(message.recipient_id)
        assert retrieved.recipient.username == "user2"
        assert retrieved.recipient.email == "user2@example.com"


class TestMessageQueryRepository:
    """Test suite for MessageQueryRepository specialized queries."""

    def test_exists_by_id_true(self, test_db_session: Session, sample_messages):
        """Test checking if message exists."""
        repo = MessageQueryRepository(test_db_session)
        existing = sample_messages[0]

        exists = repo.exists_by_id(existing.id)

        assert exists is True

    def test_exists_by_id_false(self, test_db_session: Session):
        """Test checking if non-existing message exists."""
        repo = MessageQueryRepository(test_db_session)

        exists = repo.exists_by_id(999999)

        assert exists is False
