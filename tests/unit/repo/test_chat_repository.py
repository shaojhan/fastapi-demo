"""
Unit tests for ChatRepository.
Tests the data access layer for Chat aggregates.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.ChatRepository import ChatRepository
from app.domain.ChatModel import ConversationModel


class TestChatRepositoryConversations:
    """Test suite for ChatRepository conversation operations."""

    def test_create_conversation(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created = repo.create_conversation(conv)

        assert created.id is not None
        assert created.user_id == str(user.id)
        assert created.title is None

    def test_get_conversation_existing(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created = repo.create_conversation(conv)
        test_db_session.commit()

        retrieved = repo.get_conversation(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.user_id == str(user.id)

    def test_get_conversation_non_existing(self, test_db_session: Session):
        repo = ChatRepository(test_db_session)

        retrieved = repo.get_conversation(str(uuid4()))

        assert retrieved is None

    def test_get_conversations_by_user(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        # Create 3 conversations
        for i in range(3):
            conv = ConversationModel.create(user_id=str(user.id))
            repo.create_conversation(conv)
        test_db_session.commit()

        conversations, total = repo.get_conversations_by_user(str(user.id))

        assert total == 3
        assert len(conversations) == 3

    def test_get_conversations_by_user_empty(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[1]  # No conversations

        conversations, total = repo.get_conversations_by_user(str(user.id))

        assert total == 0
        assert len(conversations) == 0

    def test_get_conversations_paginated(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        for i in range(5):
            conv = ConversationModel.create(user_id=str(user.id))
            repo.create_conversation(conv)
        test_db_session.commit()

        conversations, total = repo.get_conversations_by_user(str(user.id), page=1, size=2)

        assert total == 5
        assert len(conversations) == 2

    def test_update_conversation_title(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created = repo.create_conversation(conv)
        test_db_session.commit()

        repo.update_conversation_title(created.id, "New Title")
        test_db_session.commit()

        retrieved = repo.get_conversation(created.id)
        assert retrieved.title == "New Title"

    def test_delete_conversation(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created = repo.create_conversation(conv)
        test_db_session.commit()

        result = repo.delete_conversation(created.id)

        assert result is True
        assert repo.get_conversation(created.id) is None

    def test_delete_conversation_non_existing(self, test_db_session: Session):
        repo = ChatRepository(test_db_session)

        result = repo.delete_conversation(str(uuid4()))

        assert result is False


class TestChatRepositoryMessages:
    """Test suite for ChatRepository message operations."""

    def test_add_user_message(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        msg = repo.add_message(
            conversation_id=created_conv.id,
            role="user",
            content="Hello AI",
        )

        assert msg.id is not None
        assert msg.conversation_id == created_conv.id
        assert msg.role == "user"
        assert msg.content == "Hello AI"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_add_assistant_message_with_tool_calls(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        tool_calls = [{"id": "call_1", "function": {"name": "create_schedule", "arguments": "{}"}}]
        msg = repo.add_message(
            conversation_id=created_conv.id,
            role="assistant",
            content=None,
            tool_calls=tool_calls,
        )

        assert msg.role == "assistant"
        assert msg.content is None
        assert msg.tool_calls == tool_calls

    def test_add_tool_message(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        msg = repo.add_message(
            conversation_id=created_conv.id,
            role="tool",
            content='{"success": true}',
            tool_call_id="call_1",
        )

        assert msg.role == "tool"
        assert msg.tool_call_id == "call_1"

    def test_get_messages_ordered_by_time(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        repo.add_message(conversation_id=created_conv.id, role="user", content="First")
        repo.add_message(conversation_id=created_conv.id, role="assistant", content="Second")
        repo.add_message(conversation_id=created_conv.id, role="user", content="Third")
        test_db_session.commit()

        messages = repo.get_messages(created_conv.id)

        assert len(messages) == 3
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"

    def test_get_messages_with_limit(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        for i in range(10):
            repo.add_message(conversation_id=created_conv.id, role="user", content=f"Message {i}")
        test_db_session.commit()

        messages = repo.get_messages(created_conv.id, limit=5)

        assert len(messages) == 5

    def test_get_messages_empty_conversation(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        messages = repo.get_messages(created_conv.id)

        assert len(messages) == 0

    def test_delete_conversation_cascades_messages(self, test_db_session: Session, sample_users):
        repo = ChatRepository(test_db_session)
        user = sample_users[0]

        conv = ConversationModel.create(user_id=str(user.id))
        created_conv = repo.create_conversation(conv)
        test_db_session.commit()

        repo.add_message(conversation_id=created_conv.id, role="user", content="Test")
        repo.add_message(conversation_id=created_conv.id, role="assistant", content="Reply")
        test_db_session.commit()

        repo.delete_conversation(created_conv.id)
        test_db_session.commit()

        messages = repo.get_messages(created_conv.id)
        assert len(messages) == 0
