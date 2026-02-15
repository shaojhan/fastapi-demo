"""
Unit tests for ScheduleAgentService.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.services.ScheduleAgentService import ScheduleAgentService
from app.domain.ChatModel import ConversationModel, ChatMessageModel
from app.domain.ScheduleModel import ScheduleModel, ScheduleCreator
from app.exceptions.ChatException import (
    ConversationNotFoundError,
    ConversationAccessDeniedError,
    OllamaConnectionError,
)


# --- Test Data ---
TEST_USER_ID = str(uuid4())
TEST_USERNAME = "testuser"
TEST_CONVERSATION_ID = str(uuid4())
TEST_SCHEDULE_ID = str(uuid4())


def _make_conversation(user_id=None, title=None):
    return ConversationModel(
        id=TEST_CONVERSATION_ID,
        user_id=user_id or TEST_USER_ID,
        title=title,
        created_at=datetime.now(),
    )


def _make_schedule(schedule_id=None, title="Team Meeting"):
    return ScheduleModel.reconstitute(
        id=schedule_id or TEST_SCHEDULE_ID,
        title=title,
        description="Test",
        location="Room A",
        start_time=datetime(2024, 12, 1, 9, 0),
        end_time=datetime(2024, 12, 1, 10, 0),
        all_day=False,
        timezone="Asia/Taipei",
        creator_id=TEST_USER_ID,
        google_event_id=None,
        synced_at=None,
        created_at=datetime.now(),
        updated_at=None,
        creator=ScheduleCreator(
            user_id=TEST_USER_ID,
            username=TEST_USERNAME,
            email="test@example.com",
        ),
    )


@patch("app.services.ScheduleAgentService.OllamaClient")
@patch("app.services.ScheduleAgentService.ScheduleService")
class TestToolExecution:
    """Tests for ScheduleAgentService tool execution methods."""

    def test_tool_create_schedule(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.create_schedule.return_value = _make_schedule()

        service = ScheduleAgentService()
        result = service._tool_create_schedule(TEST_USER_ID, {
            "title": "Team Meeting",
            "start_time": "2024-12-01T09:00:00",
            "end_time": "2024-12-01T10:00:00",
            "description": "Test",
            "location": "Room A",
        })

        assert result["success"] is True
        assert result["title"] == "Team Meeting"
        mock_schedule_service.create_schedule.assert_called_once()

    def test_tool_list_schedules(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        schedules = [_make_schedule(schedule_id=str(uuid4())) for _ in range(3)]
        mock_schedule_service.list_schedules.return_value = (schedules, 3)

        service = ScheduleAgentService()
        result = service._tool_list_schedules({
            "start_from": "2024-12-01T00:00:00",
            "start_to": "2024-12-31T23:59:59",
        })

        assert result["success"] is True
        assert result["total"] == 3
        assert len(result["schedules"]) == 3

    def test_tool_list_schedules_default_params(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.list_schedules.return_value = ([], 0)

        service = ScheduleAgentService()
        result = service._tool_list_schedules({})

        mock_schedule_service.list_schedules.assert_called_once_with(
            page=1, size=20, start_from=None, start_to=None,
        )

    def test_tool_get_schedule(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.get_schedule.return_value = _make_schedule()

        service = ScheduleAgentService()
        result = service._tool_get_schedule({"schedule_id": TEST_SCHEDULE_ID})

        assert result["success"] is True
        assert result["id"] == TEST_SCHEDULE_ID
        assert result["title"] == "Team Meeting"

    def test_tool_update_schedule(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        updated = _make_schedule(title="Updated Meeting")
        mock_schedule_service.update_schedule.return_value = updated

        service = ScheduleAgentService()
        result = service._tool_update_schedule(TEST_USER_ID, {
            "schedule_id": TEST_SCHEDULE_ID,
            "title": "Updated Meeting",
        })

        assert result["success"] is True
        assert result["title"] == "Updated Meeting"

    def test_tool_delete_schedule(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.delete_schedule.return_value = None

        service = ScheduleAgentService()
        result = service._tool_delete_schedule(TEST_USER_ID, {
            "schedule_id": TEST_SCHEDULE_ID,
        })

        assert result["success"] is True
        mock_schedule_service.delete_schedule.assert_called_once_with(
            user_id=TEST_USER_ID, schedule_id=TEST_SCHEDULE_ID,
        )

    def test_tool_check_conflicts_no_conflict(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.check_conflicts.return_value = []

        service = ScheduleAgentService()
        result = service._tool_check_conflicts({
            "start_time": "2024-12-01T14:00:00",
            "end_time": "2024-12-01T15:00:00",
        })

        assert result["success"] is True
        assert result["has_conflicts"] is False
        assert result["conflict_count"] == 0

    def test_tool_check_conflicts_with_conflicts(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        conflicts = [_make_schedule(), _make_schedule(schedule_id=str(uuid4()), title="Other Meeting")]
        mock_schedule_service.check_conflicts.return_value = conflicts

        service = ScheduleAgentService()
        result = service._tool_check_conflicts({
            "start_time": "2024-12-01T09:00:00",
            "end_time": "2024-12-01T10:00:00",
        })

        assert result["success"] is True
        assert result["has_conflicts"] is True
        assert result["conflict_count"] == 2
        assert len(result["conflicts"]) == 2

    def test_tool_check_conflicts_with_exclude_id(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.check_conflicts.return_value = []

        service = ScheduleAgentService()
        service._tool_check_conflicts({
            "start_time": "2024-12-01T09:00:00",
            "end_time": "2024-12-01T10:00:00",
            "exclude_id": TEST_SCHEDULE_ID,
        })

        mock_schedule_service.check_conflicts.assert_called_once_with(
            start_time=datetime(2024, 12, 1, 9, 0),
            end_time=datetime(2024, 12, 1, 10, 0),
            exclude_id=TEST_SCHEDULE_ID,
        )

    def test_tool_suggest_available_slots(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        slots = [
            {"start_time": "2024-12-01T09:00:00", "end_time": "2024-12-01T10:00:00"},
            {"start_time": "2024-12-01T15:00:00", "end_time": "2024-12-01T16:00:00"},
        ]
        mock_schedule_service.suggest_available_slots.return_value = slots

        service = ScheduleAgentService()
        result = service._tool_suggest_available_slots({
            "date": "2024-12-01T00:00:00",
            "duration_minutes": 60,
        })

        assert result["success"] is True
        assert result["total_slots"] == 2
        assert len(result["available_slots"]) == 2

    def test_execute_tool_unknown_tool(self, MockScheduleService, MockOllamaClient):
        service = ScheduleAgentService()
        result = service._execute_tool(TEST_USER_ID, "unknown_tool", {})

        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_execute_tool_handles_exceptions(self, MockScheduleService, MockOllamaClient):
        mock_schedule_service = MockScheduleService.return_value
        mock_schedule_service.get_schedule.side_effect = Exception("DB error")

        service = ScheduleAgentService()
        result = service._execute_tool(TEST_USER_ID, "get_schedule", {
            "schedule_id": str(uuid4()),
        })

        assert result["success"] is False
        assert "DB error" in result["error"]


class TestConversationManagement:
    """Tests for conversation management methods."""

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_get_conversations(self, mock_uow_class, MockSS, MockOC):
        conversations = [_make_conversation()]
        mock_repo = MagicMock()
        mock_repo.get_conversations_by_user.return_value = (conversations, 1)

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        result, total = service.get_conversations(TEST_USER_ID)

        assert total == 1
        assert len(result) == 1
        mock_repo.get_conversations_by_user.assert_called_once_with(TEST_USER_ID, 1, 20)

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_get_conversation_messages_success(self, mock_uow_class, MockSS, MockOC):
        conv = _make_conversation()
        messages = [
            ChatMessageModel(id="1", conversation_id=TEST_CONVERSATION_ID, role="user", content="Hi", created_at=datetime.now()),
            ChatMessageModel(id="2", conversation_id=TEST_CONVERSATION_ID, role="assistant", content="Hello", created_at=datetime.now()),
            ChatMessageModel(id="3", conversation_id=TEST_CONVERSATION_ID, role="tool", content='{}', tool_call_id="call_1", created_at=datetime.now()),
        ]
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv
        mock_repo.get_messages.return_value = messages

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        result = service.get_conversation_messages(TEST_USER_ID, TEST_CONVERSATION_ID)

        # Tool messages should be filtered out
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_get_conversation_messages_not_found(self, mock_uow_class, MockSS, MockOC):
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation_messages(TEST_USER_ID, str(uuid4()))

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_get_conversation_messages_access_denied(self, mock_uow_class, MockSS, MockOC):
        conv = _make_conversation(user_id=str(uuid4()))  # Different owner
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        with pytest.raises(ConversationAccessDeniedError):
            service.get_conversation_messages(TEST_USER_ID, TEST_CONVERSATION_ID)

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatUnitOfWork")
    def test_delete_conversation_success(self, mock_uow_class, MockSS, MockOC):
        conv = _make_conversation()
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv
        mock_repo.delete_conversation.return_value = True

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        service.delete_conversation(TEST_USER_ID, TEST_CONVERSATION_ID)

        mock_repo.delete_conversation.assert_called_once_with(TEST_CONVERSATION_ID)
        mock_uow.commit.assert_called_once()

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatUnitOfWork")
    def test_delete_conversation_not_found(self, mock_uow_class, MockSS, MockOC):
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        with pytest.raises(ConversationNotFoundError):
            service.delete_conversation(TEST_USER_ID, str(uuid4()))

        mock_uow.commit.assert_not_called()

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatUnitOfWork")
    def test_delete_conversation_access_denied(self, mock_uow_class, MockSS, MockOC):
        conv = _make_conversation(user_id=str(uuid4()))
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleAgentService()
        with pytest.raises(ConversationAccessDeniedError):
            service.delete_conversation(TEST_USER_ID, TEST_CONVERSATION_ID)

        mock_repo.delete_conversation.assert_not_called()
        mock_uow.commit.assert_not_called()


class TestChatMethod:
    """Tests for the main chat method."""

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatUnitOfWork")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_chat_new_conversation(self, mock_query_uow_class, mock_uow_class, MockSS, MockOC):
        """Test chat creates a new conversation when no conversation_id provided."""
        # Mock Ollama response (no tool calls, just a text response)
        mock_ollama = MockOC.return_value
        mock_ollama.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "你好！有什麼可以幫忙的？"}}]
        })

        # Mock write UoW for creating conversation and saving messages
        mock_conv = _make_conversation()
        mock_write_repo = MagicMock()
        mock_write_repo.create_conversation.return_value = mock_conv
        mock_write_repo.add_message.return_value = None
        mock_write_repo.update_conversation_title.return_value = None

        mock_write_uow = MagicMock()
        mock_write_uow.repo = mock_write_repo
        mock_write_uow.__enter__ = MagicMock(return_value=mock_write_uow)
        mock_write_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_write_uow

        # Mock query UoW for loading history
        mock_query_repo = MagicMock()
        mock_query_repo.get_messages.return_value = []

        mock_query_uow = MagicMock()
        mock_query_uow.repo = mock_query_repo
        mock_query_uow.__enter__ = MagicMock(return_value=mock_query_uow)
        mock_query_uow.__exit__ = MagicMock(return_value=False)
        mock_query_uow_class.return_value = mock_query_uow

        import asyncio
        service = ScheduleAgentService()
        result = asyncio.get_event_loop().run_until_complete(
            service.chat(
                user_id=TEST_USER_ID,
                username=TEST_USERNAME,
                message="你好",
            )
        )

        assert result["conversation_id"] == TEST_CONVERSATION_ID
        assert result["message"] == "你好！有什麼可以幫忙的？"
        mock_write_repo.create_conversation.assert_called_once()

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_chat_existing_conversation_not_found(self, mock_uow_class, MockSS, MockOC):
        """Test chat raises error for non-existent conversation."""
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        import asyncio
        service = ScheduleAgentService()
        with pytest.raises(ConversationNotFoundError):
            asyncio.get_event_loop().run_until_complete(
                service.chat(
                    user_id=TEST_USER_ID,
                    username=TEST_USERNAME,
                    message="Hello",
                    conversation_id=str(uuid4()),
                )
            )

    @patch("app.services.ScheduleAgentService.OllamaClient")
    @patch("app.services.ScheduleAgentService.ScheduleService")
    @patch("app.services.ScheduleAgentService.ChatQueryUnitOfWork")
    def test_chat_existing_conversation_access_denied(self, mock_uow_class, MockSS, MockOC):
        """Test chat raises error when user doesn't own conversation."""
        conv = _make_conversation(user_id=str(uuid4()))
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        import asyncio
        service = ScheduleAgentService()
        with pytest.raises(ConversationAccessDeniedError):
            asyncio.get_event_loop().run_until_complete(
                service.chat(
                    user_id=TEST_USER_ID,
                    username=TEST_USERNAME,
                    message="Hello",
                    conversation_id=TEST_CONVERSATION_ID,
                )
            )
