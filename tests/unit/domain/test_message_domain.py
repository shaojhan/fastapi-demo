import pytest
from datetime import datetime
from app.domain.MessageModel import (
    MessageModel,
    MessageParticipant,
)


# --- Test Data ---
TEST_SUBJECT = "Meeting Notice"
TEST_CONTENT = "Please attend the meeting at 3pm tomorrow."
TEST_SENDER_ID = "11d200ac-48d8-4675-bfc0-a3a61af3c499"
TEST_RECIPIENT_ID = "22d200ac-48d8-4675-bfc0-a3a61af3c500"


class TestMessageParticipant:
    """測試 MessageParticipant 值物件"""

    def test_participant_creation(self):
        """
        測試建立 MessageParticipant。
        """
        participant = MessageParticipant(
            user_id=TEST_SENDER_ID,
            username="testuser",
            email="test@example.com"
        )

        assert participant.user_id == TEST_SENDER_ID
        assert participant.username == "testuser"
        assert participant.email == "test@example.com"

    def test_participant_immutability(self):
        """
        測試 MessageParticipant 是不可變的。
        """
        participant = MessageParticipant(
            user_id=TEST_SENDER_ID,
            username="testuser",
            email="test@example.com"
        )

        with pytest.raises(Exception):
            participant.username = "newuser"

    def test_participant_equality(self):
        """
        測試 MessageParticipant 相等性比較。
        """
        participant1 = MessageParticipant(
            user_id=TEST_SENDER_ID,
            username="testuser",
            email="test@example.com"
        )
        participant2 = MessageParticipant(
            user_id=TEST_SENDER_ID,
            username="testuser",
            email="test@example.com"
        )
        participant3 = MessageParticipant(
            user_id=TEST_RECIPIENT_ID,
            username="other",
            email="other@example.com"
        )

        assert participant1 == participant2
        assert participant1 != participant3


class TestMessageModelCreation:
    """測試 MessageModel 建立功能"""

    def test_message_creation_with_valid_data(self):
        """
        測試使用有效資料建立訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert isinstance(message, MessageModel)
        assert message.subject == TEST_SUBJECT
        assert message.content == TEST_CONTENT
        assert message.sender_id == TEST_SENDER_ID
        assert message.recipient_id == TEST_RECIPIENT_ID
        assert message.id is None  # ID 由資料庫生成
        assert message.is_read is False
        assert message.read_at is None
        assert message.parent_id is None

    def test_message_creation_with_parent_id(self):
        """
        測試建立回覆訊息（有 parent_id）。
        """
        message = MessageModel.create(
            subject="Re: " + TEST_SUBJECT,
            content="Got it, I will attend.",
            sender_id=TEST_RECIPIENT_ID,
            recipient_id=TEST_SENDER_ID,
            parent_id=123
        )

        assert message.parent_id == 123

    def test_message_creation_with_empty_subject_raises_error(self):
        """
        測試使用空白主題建立訊息會拋出 ValueError。
        """
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            MessageModel.create(
                subject="",
                content=TEST_CONTENT,
                sender_id=TEST_SENDER_ID,
                recipient_id=TEST_RECIPIENT_ID
            )

        with pytest.raises(ValueError, match="Subject cannot be empty"):
            MessageModel.create(
                subject="   ",
                content=TEST_CONTENT,
                sender_id=TEST_SENDER_ID,
                recipient_id=TEST_RECIPIENT_ID
            )

    def test_message_creation_with_empty_content_raises_error(self):
        """
        測試使用空白內容建立訊息會拋出 ValueError。
        """
        with pytest.raises(ValueError, match="Content cannot be empty"):
            MessageModel.create(
                subject=TEST_SUBJECT,
                content="",
                sender_id=TEST_SENDER_ID,
                recipient_id=TEST_RECIPIENT_ID
            )

        with pytest.raises(ValueError, match="Content cannot be empty"):
            MessageModel.create(
                subject=TEST_SUBJECT,
                content="   ",
                sender_id=TEST_SENDER_ID,
                recipient_id=TEST_RECIPIENT_ID
            )

    def test_message_creation_to_self_raises_error(self):
        """
        測試發送訊息給自己會拋出 ValueError。
        """
        with pytest.raises(ValueError, match="Cannot send message to yourself"):
            MessageModel.create(
                subject=TEST_SUBJECT,
                content=TEST_CONTENT,
                sender_id=TEST_SENDER_ID,
                recipient_id=TEST_SENDER_ID  # 相同的 ID
            )

    def test_message_creation_strips_whitespace(self):
        """
        測試建立訊息時會自動去除前後空白。
        """
        message = MessageModel.create(
            subject="  Subject  ",
            content="  Content  ",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.subject == "Subject"
        assert message.content == "Content"

    def test_message_creation_sets_created_at(self):
        """
        測試建立訊息會設定 created_at。
        """
        before = datetime.now()
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )
        after = datetime.now()

        assert message.created_at is not None
        assert before <= message.created_at <= after
        assert message.updated_at is None

    def test_message_creation_sets_delete_flags_to_false(self):
        """
        測試新建立的訊息刪除標記為 False。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.deleted_by_sender is False
        assert message.deleted_by_recipient is False


class TestMessageModelReconstitute:
    """測試 MessageModel reconstitute 工廠方法"""

    def test_reconstitute_creates_message_from_persistence(self):
        """
        測試從持久化資料重建訊息。
        """
        created_at = datetime(2024, 1, 10, 8, 0, 0)
        read_at = datetime(2024, 1, 10, 9, 0, 0)

        message = MessageModel.reconstitute(
            id=123,
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=True,
            read_at=read_at,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=created_at,
            updated_at=None
        )

        assert message.id == 123
        assert message.subject == TEST_SUBJECT
        assert message.content == TEST_CONTENT
        assert message.sender_id == TEST_SENDER_ID
        assert message.recipient_id == TEST_RECIPIENT_ID
        assert message.is_read is True
        assert message.read_at == read_at
        assert message.created_at == created_at

    def test_reconstitute_with_participants(self):
        """
        測試重建訊息時包含參與者資訊。
        """
        sender = MessageParticipant(
            user_id=TEST_SENDER_ID,
            username="sender",
            email="sender@example.com"
        )
        recipient = MessageParticipant(
            user_id=TEST_RECIPIENT_ID,
            username="recipient",
            email="recipient@example.com"
        )

        message = MessageModel.reconstitute(
            id=123,
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None,
            sender=sender,
            recipient=recipient
        )

        assert message.sender is not None
        assert message.sender.username == "sender"
        assert message.recipient is not None
        assert message.recipient.username == "recipient"

    def test_reconstitute_with_reply_count(self):
        """
        測試重建訊息時包含回覆數量。
        """
        message = MessageModel.reconstitute(
            id=123,
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None,
            reply_count=5
        )

        assert message.reply_count == 5


class TestMessageModelMarkAsRead:
    """測試訊息標記為已讀功能"""

    def test_mark_as_read_updates_status(self):
        """
        測試標記為已讀會更新狀態。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.is_read is False
        assert message.read_at is None

        message.mark_as_read()

        assert message.is_read is True
        assert message.read_at is not None
        assert message.updated_at is not None

    def test_mark_as_read_sets_read_at_time(self):
        """
        測試標記為已讀會設定閱讀時間。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        before = datetime.now()
        message.mark_as_read()
        after = datetime.now()

        assert before <= message.read_at <= after

    def test_mark_already_read_message_raises_error(self):
        """
        測試對已讀訊息再次標記會拋出 ValueError。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )
        message.mark_as_read()

        with pytest.raises(ValueError, match="Message is already read"):
            message.mark_as_read()


class TestMessageModelDelete:
    """測試訊息刪除功能"""

    def test_delete_for_sender(self):
        """
        測試發送者刪除訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        message.delete_for_sender()

        assert message.deleted_by_sender is True
        assert message.deleted_by_recipient is False
        assert message.updated_at is not None

    def test_delete_for_recipient(self):
        """
        測試接收者刪除訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        message.delete_for_recipient()

        assert message.deleted_by_sender is False
        assert message.deleted_by_recipient is True
        assert message.updated_at is not None

    def test_delete_by_both_parties(self):
        """
        測試雙方都刪除訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        message.delete_for_sender()
        message.delete_for_recipient()

        assert message.deleted_by_sender is True
        assert message.deleted_by_recipient is True


class TestMessageModelIsReply:
    """測試訊息回覆判斷功能"""

    def test_is_reply_returns_false_for_original_message(self):
        """
        測試原始訊息 is_reply 返回 False。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.is_reply() is False

    def test_is_reply_returns_true_for_reply_message(self):
        """
        測試回覆訊息 is_reply 返回 True。
        """
        message = MessageModel.create(
            subject="Re: " + TEST_SUBJECT,
            content="Got it.",
            sender_id=TEST_RECIPIENT_ID,
            recipient_id=TEST_SENDER_ID,
            parent_id=123
        )

        assert message.is_reply() is True


class TestMessageModelCanView:
    """測試訊息查看權限"""

    def test_can_view_returns_true_for_sender(self):
        """
        測試發送者可以查看訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.can_view(TEST_SENDER_ID) is True

    def test_can_view_returns_true_for_recipient(self):
        """
        測試接收者可以查看訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.can_view(TEST_RECIPIENT_ID) is True

    def test_can_view_returns_false_for_other_user(self):
        """
        測試其他使用者無法查看訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        other_user_id = "33d200ac-48d8-4675-bfc0-a3a61af3c501"
        assert message.can_view(other_user_id) is False

    def test_can_view_returns_false_for_sender_after_delete(self):
        """
        測試發送者刪除後無法查看訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )
        message.delete_for_sender()

        assert message.can_view(TEST_SENDER_ID) is False
        assert message.can_view(TEST_RECIPIENT_ID) is True

    def test_can_view_returns_false_for_recipient_after_delete(self):
        """
        測試接收者刪除後無法查看訊息。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )
        message.delete_for_recipient()

        assert message.can_view(TEST_SENDER_ID) is True
        assert message.can_view(TEST_RECIPIENT_ID) is False


class TestMessageModelEquality:
    """測試訊息相等性"""

    def test_message_equality_by_id(self):
        """
        測試訊息相等性基於 ID 判斷。
        """
        message1 = MessageModel.reconstitute(
            id=123,
            subject="Subject 1",
            content="Content 1",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )
        message2 = MessageModel.reconstitute(
            id=123,
            subject="Subject 2",  # 不同主題
            content="Content 2",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )
        message3 = MessageModel.reconstitute(
            id=456,
            subject="Subject 1",
            content="Content 1",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )

        assert message1 == message2  # 相同 ID 應該相等
        assert message1 != message3  # 不同 ID 應該不相等

    def test_message_hash_consistency(self):
        """
        測試訊息雜湊值一致性。
        """
        message1 = MessageModel.reconstitute(
            id=123,
            subject="Subject 1",
            content="Content 1",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )
        message2 = MessageModel.reconstitute(
            id=123,
            subject="Subject 2",
            content="Content 2",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )

        assert hash(message1) == hash(message2)

    def test_message_can_be_used_in_set(self):
        """
        測試訊息可以用於集合操作。
        """
        message1 = MessageModel.reconstitute(
            id=123,
            subject="Subject 1",
            content="Content 1",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )
        message2 = MessageModel.reconstitute(
            id=456,
            subject="Subject 2",
            content="Content 2",
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID,
            is_read=False,
            read_at=None,
            parent_id=None,
            deleted_by_sender=False,
            deleted_by_recipient=False,
            created_at=datetime.now(),
            updated_at=None
        )

        message_set = {message1, message2}

        assert len(message_set) == 2


class TestMessageModelReplyCount:
    """測試訊息回覆數量功能"""

    def test_reply_count_default_value(self):
        """
        測試回覆數量預設值為 0。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        assert message.reply_count == 0

    def test_reply_count_setter(self):
        """
        測試設定回覆數量。
        """
        message = MessageModel.create(
            subject=TEST_SUBJECT,
            content=TEST_CONTENT,
            sender_id=TEST_SENDER_ID,
            recipient_id=TEST_RECIPIENT_ID
        )

        message.reply_count = 10

        assert message.reply_count == 10
