"""
Unit tests for ChatModel domain objects.
"""
import pytest
from datetime import datetime, timezone
from uuid import UUID

from app.domain.ChatModel import ConversationModel, ChatMessageModel


# --- Test Data ---
TEST_USER_ID = "11d200ac-48d8-4675-bfc0-a3a61af3c499"
TEST_OTHER_USER_ID = "22e300bd-59e9-5786-cge1-b4b72bg4d500"


class TestChatMessageModel:
    """Tests for ChatMessageModel value object."""

    def test_create_user_message(self):
        msg = ChatMessageModel(
            id="msg-1",
            conversation_id="conv-1",
            role="user",
            content="Hello",
        )
        assert msg.id == "msg-1"
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_assistant_message_with_tool_calls(self):
        tool_calls = [{"id": "call_1", "function": {"name": "create_schedule", "arguments": "{}"}}]
        msg = ChatMessageModel(
            id="msg-2",
            conversation_id="conv-1",
            role="assistant",
            content=None,
            tool_calls=tool_calls,
        )
        assert msg.role == "assistant"
        assert msg.content is None
        assert msg.tool_calls == tool_calls

    def test_create_tool_message(self):
        msg = ChatMessageModel(
            id="msg-3",
            conversation_id="conv-1",
            role="tool",
            content='{"success": true}',
            tool_call_id="call_1",
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_1"

    def test_message_immutability(self):
        msg = ChatMessageModel(
            id="msg-1",
            conversation_id="conv-1",
            role="user",
            content="Hello",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            msg.content = "Modified"


class TestConversationModel:
    """Tests for ConversationModel aggregate root."""

    def test_create_conversation(self):
        conv = ConversationModel.create(user_id=TEST_USER_ID)

        assert conv.id is not None
        try:
            UUID(conv.id, version=4)
        except ValueError:
            pytest.fail("Conversation ID should be a valid UUIDv4")
        assert conv.user_id == TEST_USER_ID
        assert conv.title is None
        assert conv.messages == []
        assert conv.created_at is not None

    def test_create_generates_unique_ids(self):
        conv1 = ConversationModel.create(user_id=TEST_USER_ID)
        conv2 = ConversationModel.create(user_id=TEST_USER_ID)
        assert conv1.id != conv2.id

    def test_set_title(self):
        conv = ConversationModel.create(user_id=TEST_USER_ID)
        conv.set_title("My Conversation")

        assert conv.title == "My Conversation"
        assert conv.updated_at is not None

    def test_set_title_truncates_long_string(self):
        conv = ConversationModel.create(user_id=TEST_USER_ID)
        long_title = "A" * 300
        conv.set_title(long_title)

        assert len(conv.title) == 255

    def test_set_title_none(self):
        conv = ConversationModel.create(user_id=TEST_USER_ID)
        conv.set_title("Some title")
        conv.set_title(None)

        assert conv.title is None

    def test_is_owner_returns_true_for_owner(self):
        conv = ConversationModel.create(user_id=TEST_USER_ID)
        assert conv.is_owner(TEST_USER_ID) is True

    def test_is_owner_returns_false_for_other_user(self):
        conv = ConversationModel.create(user_id=TEST_USER_ID)
        assert conv.is_owner(TEST_OTHER_USER_ID) is False

    def test_equality_by_id(self):
        conv1 = ConversationModel(id="same-id", user_id=TEST_USER_ID)
        conv2 = ConversationModel(id="same-id", user_id=TEST_OTHER_USER_ID)
        conv3 = ConversationModel(id="different-id", user_id=TEST_USER_ID)

        assert conv1 == conv2
        assert conv1 != conv3

    def test_hash_consistency(self):
        conv1 = ConversationModel(id="same-id", user_id=TEST_USER_ID)
        conv2 = ConversationModel(id="same-id", user_id=TEST_OTHER_USER_ID)

        assert hash(conv1) == hash(conv2)

    def test_can_be_used_in_set(self):
        conv1 = ConversationModel.create(user_id=TEST_USER_ID)
        conv2 = ConversationModel.create(user_id=TEST_USER_ID)
        conv_set = {conv1, conv2}

        assert len(conv_set) == 2
