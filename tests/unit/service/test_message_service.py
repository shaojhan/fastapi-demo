"""
Unit tests for MessageService.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from uuid import uuid4, UUID

from app.services.MessageService import MessageService
from app.domain.MessageModel import MessageModel, MessageParticipant
from app.domain.UserModel import UserModel, UserRole, Profile, HashedPassword
from app.exceptions.MessageException import (
    MessageNotFoundError,
    MessageAccessDeniedError,
    RecipientNotFoundError,
)
from app.router.schemas.MessageSchema import SendMessageRequest, ReplyMessageRequest


# --- Test Data ---
TEST_SENDER_ID = str(uuid4())
TEST_RECIPIENT_ID = str(uuid4())
TEST_MESSAGE_ID = 1
TEST_SUBJECT = "Test Subject"
TEST_CONTENT = "Test message content"


def _make_message_model(
    message_id=TEST_MESSAGE_ID,
    sender_id=None,
    recipient_id=None,
    subject=TEST_SUBJECT,
    content=TEST_CONTENT,
    is_read=False,
    parent_id=None,
) -> MessageModel:
    """Create a test MessageModel."""
    sender_user_id = sender_id or TEST_SENDER_ID
    recipient_user_id = recipient_id or TEST_RECIPIENT_ID
    return MessageModel.reconstitute(
        id=message_id,
        subject=subject,
        content=content,
        sender_id=sender_user_id,
        recipient_id=recipient_user_id,
        is_read=is_read,
        read_at=datetime.now() if is_read else None,
        parent_id=parent_id,
        deleted_by_sender=False,
        deleted_by_recipient=False,
        created_at=datetime.now(),
        updated_at=None,
        sender=MessageParticipant(
            user_id=sender_user_id,
            username="sender",
            email="sender@example.com"
        ),
        recipient=MessageParticipant(
            user_id=recipient_user_id,
            username="recipient",
            email="recipient@example.com"
        )
    )


def _make_user_model(user_id=None) -> UserModel:
    """Create a test UserModel."""
    return UserModel.reconstitute(
        id=user_id or TEST_RECIPIENT_ID,
        uid="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        profile=Profile(),
        role=UserRole.NORMAL
    )


class TestSendMessage:
    """Tests for MessageService.send_message"""

    @patch("app.services.MessageService.MessageUnitOfWork")
    @patch("app.services.MessageService.UserUnitOfWork")
    def test_send_message_success(self, mock_user_uow_class, mock_msg_uow_class):
        """Test sending a message successfully."""
        # Arrange
        recipient = _make_user_model(TEST_RECIPIENT_ID)
        created_message = _make_message_model()

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = recipient

        mock_user_uow = MagicMock()
        mock_user_uow.repo = mock_user_repo
        mock_user_uow.__enter__ = MagicMock(return_value=mock_user_uow)
        mock_user_uow.__exit__ = MagicMock(return_value=False)
        mock_user_uow_class.return_value = mock_user_uow

        mock_msg_repo = MagicMock()
        mock_msg_repo.add.return_value = created_message

        mock_msg_uow = MagicMock()
        mock_msg_uow.repo = mock_msg_repo
        mock_msg_uow.__enter__ = MagicMock(return_value=mock_msg_uow)
        mock_msg_uow.__exit__ = MagicMock(return_value=False)
        mock_msg_uow_class.return_value = mock_msg_uow

        request = SendMessageRequest(
            recipient_id=UUID(TEST_RECIPIENT_ID),
            subject=TEST_SUBJECT,
            content=TEST_CONTENT
        )

        # Act
        service = MessageService()
        result = service.send_message(sender_id=TEST_SENDER_ID, request=request)

        # Assert
        mock_user_repo.get_by_id.assert_called_once_with(TEST_RECIPIENT_ID)
        mock_msg_repo.add.assert_called_once()
        mock_msg_uow.commit.assert_called_once()
        assert result.subject == TEST_SUBJECT

    @patch("app.services.MessageService.UserUnitOfWork")
    def test_send_message_recipient_not_found(self, mock_user_uow_class):
        """Test sending message to non-existent recipient raises error."""
        # Arrange
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = None

        mock_user_uow = MagicMock()
        mock_user_uow.repo = mock_user_repo
        mock_user_uow.__enter__ = MagicMock(return_value=mock_user_uow)
        mock_user_uow.__exit__ = MagicMock(return_value=False)
        mock_user_uow_class.return_value = mock_user_uow

        request = SendMessageRequest(
            recipient_id=UUID(str(uuid4())),
            subject=TEST_SUBJECT,
            content=TEST_CONTENT
        )

        # Act & Assert
        service = MessageService()
        with pytest.raises(RecipientNotFoundError):
            service.send_message(sender_id=TEST_SENDER_ID, request=request)


class TestReplyMessage:
    """Tests for MessageService.reply_message"""

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_reply_message_as_recipient_success(self, mock_uow_class):
        """Test replying to a message as the recipient."""
        # Arrange
        original_message = _make_message_model()
        reply_message = _make_message_model(
            message_id=2,
            sender_id=TEST_RECIPIENT_ID,
            recipient_id=TEST_SENDER_ID,
            subject=f"Re: {TEST_SUBJECT}",
            parent_id=TEST_MESSAGE_ID
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = original_message
        mock_repo.add.return_value = reply_message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        request = ReplyMessageRequest(content="Reply content")

        # Act
        service = MessageService()
        result = service.reply_message(
            user_id=TEST_RECIPIENT_ID,
            message_id=TEST_MESSAGE_ID,
            request=request
        )

        # Assert
        mock_repo.get_by_id.assert_called_once_with(TEST_MESSAGE_ID)
        mock_repo.add.assert_called_once()
        mock_uow.commit.assert_called_once()
        assert result.parent_id == TEST_MESSAGE_ID

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_reply_message_as_sender_success(self, mock_uow_class):
        """Test replying to a message as the sender."""
        # Arrange
        original_message = _make_message_model()
        reply_message = _make_message_model(
            message_id=2,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            subject=f"Re: {TEST_SUBJECT}",
            parent_id=TEST_MESSAGE_ID
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = original_message
        mock_repo.add.return_value = reply_message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        request = ReplyMessageRequest(content="Reply content")

        # Act
        service = MessageService()
        result = service.reply_message(
            user_id=TEST_SENDER_ID,
            message_id=TEST_MESSAGE_ID,
            request=request
        )

        # Assert
        mock_repo.add.assert_called_once()
        mock_uow.commit.assert_called_once()

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_reply_message_not_found(self, mock_uow_class):
        """Test replying to non-existent message raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        request = ReplyMessageRequest(content="Reply content")

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageNotFoundError):
            service.reply_message(
                user_id=TEST_SENDER_ID,
                message_id=999,
                request=request
            )

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_reply_message_access_denied(self, mock_uow_class):
        """Test replying to message by non-participant raises error."""
        # Arrange
        original_message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = original_message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        request = ReplyMessageRequest(content="Reply content")
        other_user_id = str(uuid4())

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageAccessDeniedError):
            service.reply_message(
                user_id=other_user_id,
                message_id=TEST_MESSAGE_ID,
                request=request
            )


class TestGetInbox:
    """Tests for MessageService.get_inbox"""

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_inbox_success(self, mock_uow_class):
        """Test getting user inbox."""
        # Arrange
        messages = [
            _make_message_model(message_id=1),
            _make_message_model(message_id=2),
        ]

        mock_repo = MagicMock()
        mock_repo.get_inbox.return_value = (messages, 2)
        mock_repo.get_unread_count.return_value = 1
        mock_repo.get_reply_count.return_value = 0

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        result_messages, total, unread = service.get_inbox(
            user_id=TEST_RECIPIENT_ID,
            page=1,
            size=20
        )

        # Assert
        mock_repo.get_inbox.assert_called_once_with(TEST_RECIPIENT_ID, 1, 20)
        mock_repo.get_unread_count.assert_called_once_with(TEST_RECIPIENT_ID)
        assert len(result_messages) == 2
        assert total == 2
        assert unread == 1

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_inbox_empty(self, mock_uow_class):
        """Test getting empty inbox."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_inbox.return_value = ([], 0)
        mock_repo.get_unread_count.return_value = 0

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        result_messages, total, unread = service.get_inbox(
            user_id=TEST_RECIPIENT_ID,
            page=1,
            size=20
        )

        # Assert
        assert len(result_messages) == 0
        assert total == 0
        assert unread == 0


class TestGetSent:
    """Tests for MessageService.get_sent"""

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_sent_success(self, mock_uow_class):
        """Test getting user sent messages."""
        # Arrange
        messages = [
            _make_message_model(message_id=1),
        ]

        mock_repo = MagicMock()
        mock_repo.get_sent.return_value = (messages, 1)
        mock_repo.get_reply_count.return_value = 2

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        result_messages, total = service.get_sent(
            user_id=TEST_SENDER_ID,
            page=1,
            size=20
        )

        # Assert
        mock_repo.get_sent.assert_called_once_with(TEST_SENDER_ID, 1, 20)
        assert len(result_messages) == 1
        assert total == 1


class TestGetMessage:
    """Tests for MessageService.get_message"""

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_message_success(self, mock_uow_class):
        """Test getting a single message."""
        # Arrange
        message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message
        mock_repo.get_reply_count.return_value = 3

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        result = service.get_message(user_id=TEST_SENDER_ID, message_id=TEST_MESSAGE_ID)

        # Assert
        mock_repo.get_by_id.assert_called_once_with(TEST_MESSAGE_ID)
        assert result.id == TEST_MESSAGE_ID
        assert result.reply_count == 3

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_message_not_found(self, mock_uow_class):
        """Test getting non-existent message raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageNotFoundError):
            service.get_message(user_id=TEST_SENDER_ID, message_id=999)

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_message_access_denied(self, mock_uow_class):
        """Test getting message by non-participant raises error."""
        # Arrange
        message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        other_user_id = str(uuid4())

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageAccessDeniedError):
            service.get_message(user_id=other_user_id, message_id=TEST_MESSAGE_ID)


class TestGetThread:
    """Tests for MessageService.get_thread"""

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_thread_success(self, mock_uow_class):
        """Test getting message thread."""
        # Arrange
        original = _make_message_model(message_id=1)
        replies = [
            _make_message_model(message_id=2, parent_id=1),
            _make_message_model(message_id=3, parent_id=1),
        ]

        mock_repo = MagicMock()
        mock_repo.get_thread.return_value = (original, replies)

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        result_original, result_replies = service.get_thread(
            user_id=TEST_SENDER_ID,
            message_id=1
        )

        # Assert
        mock_repo.get_thread.assert_called_once_with(1)
        assert result_original.id == 1
        assert len(result_replies) == 2

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_thread_not_found(self, mock_uow_class):
        """Test getting non-existent thread raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_thread.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageNotFoundError):
            service.get_thread(user_id=TEST_SENDER_ID, message_id=999)

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_thread_access_denied(self, mock_uow_class):
        """Test getting thread by non-participant raises error."""
        # Arrange
        original = _make_message_model()
        replies = []

        mock_repo = MagicMock()
        mock_repo.get_thread.return_value = (original, replies)

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        other_user_id = str(uuid4())

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageAccessDeniedError):
            service.get_thread(user_id=other_user_id, message_id=TEST_MESSAGE_ID)


class TestMarkAsRead:
    """Tests for MessageService.mark_as_read"""

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_mark_as_read_success(self, mock_uow_class):
        """Test marking a message as read."""
        # Arrange
        message = _make_message_model(is_read=False)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message
        mock_repo.mark_as_read.return_value = True

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        service.mark_as_read(user_id=TEST_RECIPIENT_ID, message_id=TEST_MESSAGE_ID)

        # Assert
        mock_repo.mark_as_read.assert_called_once_with(TEST_MESSAGE_ID)
        mock_uow.commit.assert_called_once()

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_mark_as_read_already_read(self, mock_uow_class):
        """Test marking already read message doesn't update."""
        # Arrange
        message = _make_message_model(is_read=True)

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        service.mark_as_read(user_id=TEST_RECIPIENT_ID, message_id=TEST_MESSAGE_ID)

        # Assert
        mock_repo.mark_as_read.assert_not_called()

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_mark_as_read_not_found(self, mock_uow_class):
        """Test marking non-existent message raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageNotFoundError):
            service.mark_as_read(user_id=TEST_RECIPIENT_ID, message_id=999)

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_mark_as_read_access_denied(self, mock_uow_class):
        """Test marking message by non-recipient raises error."""
        # Arrange
        message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageAccessDeniedError):
            service.mark_as_read(user_id=TEST_SENDER_ID, message_id=TEST_MESSAGE_ID)


class TestBatchMarkAsRead:
    """Tests for MessageService.batch_mark_as_read"""

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_batch_mark_as_read_success(self, mock_uow_class):
        """Test batch marking messages as read."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.batch_mark_as_read.return_value = 3

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        message_ids = [1, 2, 3]

        # Act
        service = MessageService()
        count = service.batch_mark_as_read(user_id=TEST_RECIPIENT_ID, message_ids=message_ids)

        # Assert
        mock_repo.batch_mark_as_read.assert_called_once_with(message_ids, TEST_RECIPIENT_ID)
        mock_uow.commit.assert_called_once()
        assert count == 3


class TestDeleteMessage:
    """Tests for MessageService.delete_message"""

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_delete_message_as_sender(self, mock_uow_class):
        """Test deleting a message as sender."""
        # Arrange
        message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message
        mock_repo.soft_delete.return_value = True

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        service.delete_message(user_id=TEST_SENDER_ID, message_id=TEST_MESSAGE_ID)

        # Assert
        mock_repo.soft_delete.assert_called_once_with(TEST_MESSAGE_ID, TEST_SENDER_ID, True)
        mock_uow.commit.assert_called_once()

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_delete_message_as_recipient(self, mock_uow_class):
        """Test deleting a message as recipient."""
        # Arrange
        message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message
        mock_repo.soft_delete.return_value = True

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        service.delete_message(user_id=TEST_RECIPIENT_ID, message_id=TEST_MESSAGE_ID)

        # Assert
        mock_repo.soft_delete.assert_called_once_with(TEST_MESSAGE_ID, TEST_RECIPIENT_ID, False)
        mock_uow.commit.assert_called_once()

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_delete_message_not_found(self, mock_uow_class):
        """Test deleting non-existent message raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageNotFoundError):
            service.delete_message(user_id=TEST_SENDER_ID, message_id=999)

    @patch("app.services.MessageService.MessageUnitOfWork")
    def test_delete_message_access_denied(self, mock_uow_class):
        """Test deleting message by non-participant raises error."""
        # Arrange
        message = _make_message_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = message

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        other_user_id = str(uuid4())

        # Act & Assert
        service = MessageService()
        with pytest.raises(MessageAccessDeniedError):
            service.delete_message(user_id=other_user_id, message_id=TEST_MESSAGE_ID)


class TestGetUnreadCount:
    """Tests for MessageService.get_unread_count"""

    @patch("app.services.MessageService.MessageQueryUnitOfWork")
    def test_get_unread_count_success(self, mock_uow_class):
        """Test getting unread count."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_unread_count.return_value = 5

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = MessageService()
        count = service.get_unread_count(user_id=TEST_RECIPIENT_ID)

        # Assert
        mock_repo.get_unread_count.assert_called_once_with(TEST_RECIPIENT_ID)
        assert count == 5
