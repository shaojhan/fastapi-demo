"""
Unit tests for MQTTSummaryService.

測試策略:
- Mock MQTTUnitOfWork, UserQueryUnitOfWork, OllamaClient, EmailService
- 驗證各私有方法的行為與錯誤處理
- 驗證 generate_and_send() 的完整流程與計數
"""
import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

import httpx

from app.services.MQTTSummaryService import MQTTSummaryService
from app.domain.MQTTModel import MQTTMessageModel
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile


# ── Test Data ──────────────────────────────────────────────────────────────

def _make_mqtt_message(topic="sensors/temp", payload="25.5", hours_ago=1):
    return MQTTMessageModel.reconstitute(
        id=1,
        topic=topic,
        payload=payload,
        qos=0,
        received_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    )


def _make_user(email="user@example.com", email_verified=True):
    return UserModel.reconstitute(
        id=str(uuid4()),
        uid="user",
        email=email,
        hashed_password="hashed",
        profile=DomainProfile(name="Test User"),
        role=UserRole.EMPLOYEE,
        email_verified=email_verified,
    )


def _setup_uow_mock(mock_uow_class, repo=None):
    mock_uow = MagicMock()
    mock_uow.repo = repo or MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow
    return mock_uow


# ── TestFetchRecentMessages ────────────────────────────────────────────────

@patch("app.services.MQTTSummaryService.OllamaClient")
@patch("app.services.MQTTSummaryService.EmailService")
@patch("app.services.MQTTSummaryService.MQTTUnitOfWork")
class TestFetchRecentMessages:

    def test_calls_repo_with_received_after(self, MockUoW, MockEmail, MockOllama):
        messages = [_make_mqtt_message()]
        mock_repo = MagicMock()
        mock_repo.get_messages.return_value = (messages, 1)
        _setup_uow_mock(MockUoW, repo=mock_repo)

        service = MQTTSummaryService()
        result = service._fetch_recent_messages(hours=24)

        assert result == messages
        call_kwargs = mock_repo.get_messages.call_args.kwargs
        assert "received_after" in call_kwargs
        # cutoff should be approximately 24 hours ago
        cutoff: datetime = call_kwargs["received_after"]
        expected = datetime.now(timezone.utc) - timedelta(hours=24)
        assert abs((cutoff - expected).total_seconds()) < 5

    def test_returns_empty_list_when_no_messages(self, MockUoW, MockEmail, MockOllama):
        mock_repo = MagicMock()
        mock_repo.get_messages.return_value = ([], 0)
        _setup_uow_mock(MockUoW, repo=mock_repo)

        service = MQTTSummaryService()
        result = service._fetch_recent_messages(hours=24)

        assert result == []

    def test_passes_size_500_cap(self, MockUoW, MockEmail, MockOllama):
        mock_repo = MagicMock()
        mock_repo.get_messages.return_value = ([], 0)
        _setup_uow_mock(MockUoW, repo=mock_repo)

        service = MQTTSummaryService()
        service._fetch_recent_messages(hours=1)

        call_kwargs = mock_repo.get_messages.call_args.kwargs
        assert call_kwargs.get("size") == 500


# ── TestGenerateSummary ────────────────────────────────────────────────────

@patch("app.services.MQTTSummaryService.OllamaClient")
@patch("app.services.MQTTSummaryService.EmailService")
class TestGenerateSummary:

    def test_returns_ollama_response(self, MockEmail, MockOllama):
        mock_ollama = MockOllama.return_value
        mock_ollama.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "摘要結果"}}]
        })

        messages = [_make_mqtt_message()]
        service = MQTTSummaryService()
        result = asyncio.run(service._generate_summary(messages, hours=24))

        assert result == "摘要結果"

    def test_calls_ollama_with_traditional_chinese_system_prompt(
        self, MockEmail, MockOllama
    ):
        mock_ollama = MockOllama.return_value
        mock_ollama.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "ok"}}]
        })

        messages = [_make_mqtt_message()]
        service = MQTTSummaryService()
        asyncio.run(service._generate_summary(messages, hours=24))

        call_args = mock_ollama.chat_completion.call_args
        prompt_messages = call_args.args[0]
        system_content = prompt_messages[0]["content"]
        assert "繁體中文" in system_content

    def test_returns_fallback_on_ollama_connect_error(self, MockEmail, MockOllama):
        mock_ollama = MockOllama.return_value
        mock_ollama.chat_completion = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )

        messages = [_make_mqtt_message()]
        service = MQTTSummaryService()
        result = asyncio.run(service._generate_summary(messages, hours=24))

        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_messages_skips_ollama(self, MockEmail, MockOllama):
        mock_ollama = MockOllama.return_value

        service = MQTTSummaryService()
        result = asyncio.run(service._generate_summary([], hours=24))

        mock_ollama.chat_completion.assert_not_called()
        assert "沒有收到任何 MQTT 訊息" in result


# ── TestGetRecipientEmails ─────────────────────────────────────────────────

@patch("app.services.MQTTSummaryService.OllamaClient")
@patch("app.services.MQTTSummaryService.EmailService")
@patch("app.services.MQTTSummaryService.UserQueryUnitOfWork")
class TestGetRecipientEmails:

    def test_returns_only_verified_user_emails(
        self, MockQueryUoW, MockEmail, MockOllama
    ):
        verified = _make_user(email="verified@example.com", email_verified=True)
        unverified = _make_user(email="unverified@example.com", email_verified=False)

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = ([verified, unverified], 2)

        mock_uow = MagicMock()
        mock_uow.query_repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        MockQueryUoW.return_value = mock_uow

        service = MQTTSummaryService()
        result = service._get_recipient_emails()

        assert result == ["verified@example.com"]

    def test_returns_empty_list_when_no_verified_users(
        self, MockQueryUoW, MockEmail, MockOllama
    ):
        unverified = _make_user(email_verified=False)

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = ([unverified], 1)

        mock_uow = MagicMock()
        mock_uow.query_repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        MockQueryUoW.return_value = mock_uow

        service = MQTTSummaryService()
        result = service._get_recipient_emails()

        assert result == []


# ── TestGenerateAndSend ────────────────────────────────────────────────────

@patch("app.services.MQTTSummaryService.OllamaClient")
@patch("app.services.MQTTSummaryService.EmailService")
@patch("app.services.MQTTSummaryService.MQTTUnitOfWork")
@patch("app.services.MQTTSummaryService.UserQueryUnitOfWork")
class TestGenerateAndSend:

    def _setup(self, MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama,
               messages=None, users=None):
        # MQTT repo
        mock_mqtt_repo = MagicMock()
        mock_mqtt_repo.get_messages.return_value = (messages or [], len(messages or []))
        _setup_uow_mock(MockMQTTUoW, repo=mock_mqtt_repo)

        # User query repo
        mock_user_repo = MagicMock()
        mock_user_repo.get_all.return_value = (users or [], len(users or []))
        mock_query_uow = MagicMock()
        mock_query_uow.query_repo = mock_user_repo
        mock_query_uow.__enter__ = MagicMock(return_value=mock_query_uow)
        mock_query_uow.__exit__ = MagicMock(return_value=False)
        MockQueryUoW.return_value = mock_query_uow

        # Ollama
        mock_ollama = MockOllama.return_value
        mock_ollama.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "AI 摘要文字"}}]
        })

        # Email
        mock_email = MockEmail.return_value
        mock_email.send_summary_email = AsyncMock()
        return mock_email

    def test_full_pipeline_returns_correct_counts(
        self, MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama
    ):
        messages = [_make_mqtt_message(), _make_mqtt_message(topic="sensors/humidity")]
        users = [
            _make_user("a@test.com"), _make_user("b@test.com")
        ]
        self._setup(MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama,
                    messages=messages, users=users)

        service = MQTTSummaryService()
        result = asyncio.run(service.generate_and_send(hours=24))

        assert result["message_count"] == 2
        assert result["recipient_count"] == 2
        assert result["sent_count"] == 2
        assert result["failed_count"] == 0

    def test_partial_send_failure_does_not_raise(
        self, MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama
    ):
        messages = [_make_mqtt_message()]
        users = [_make_user("ok@test.com"), _make_user("fail@test.com")]
        mock_email = self._setup(MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama,
                                  messages=messages, users=users)

        call_count = 0

        async def side_effect(email, summary, hours):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("SMTP error")

        mock_email.send_summary_email = side_effect

        service = MQTTSummaryService()
        result = asyncio.run(service.generate_and_send(hours=24))

        assert result["sent_count"] == 1
        assert result["failed_count"] == 1

    def test_hours_none_uses_config_default(
        self, MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama
    ):
        mock_mqtt_repo = MagicMock()
        mock_mqtt_repo.get_messages.return_value = ([], 0)
        _setup_uow_mock(MockMQTTUoW, repo=mock_mqtt_repo)

        mock_user_repo = MagicMock()
        mock_user_repo.get_all.return_value = ([], 0)
        mock_query_uow = MagicMock()
        mock_query_uow.query_repo = mock_user_repo
        mock_query_uow.__enter__ = MagicMock(return_value=mock_query_uow)
        mock_query_uow.__exit__ = MagicMock(return_value=False)
        MockQueryUoW.return_value = mock_query_uow

        MockOllama.return_value.chat_completion = AsyncMock(
            return_value={"choices": [{"message": {"content": "ok"}}]}
        )

        service = MQTTSummaryService()
        asyncio.run(service.generate_and_send(hours=None))

        call_kwargs = mock_mqtt_repo.get_messages.call_args.kwargs
        expected_hours = service.settings.MQTT_SUMMARY_HOURS
        cutoff = call_kwargs["received_after"]
        expected = datetime.now(timezone.utc) - timedelta(hours=expected_hours)
        assert abs((cutoff - expected).total_seconds()) < 5

    def test_hours_override_respected(
        self, MockQueryUoW, MockMQTTUoW, MockEmail, MockOllama
    ):
        mock_mqtt_repo = MagicMock()
        mock_mqtt_repo.get_messages.return_value = ([], 0)
        _setup_uow_mock(MockMQTTUoW, repo=mock_mqtt_repo)

        mock_user_repo = MagicMock()
        mock_user_repo.get_all.return_value = ([], 0)
        mock_query_uow = MagicMock()
        mock_query_uow.query_repo = mock_user_repo
        mock_query_uow.__enter__ = MagicMock(return_value=mock_query_uow)
        mock_query_uow.__exit__ = MagicMock(return_value=False)
        MockQueryUoW.return_value = mock_query_uow

        MockOllama.return_value.chat_completion = AsyncMock(
            return_value={"choices": [{"message": {"content": "ok"}}]}
        )

        service = MQTTSummaryService()
        asyncio.run(service.generate_and_send(hours=48))

        call_kwargs = mock_mqtt_repo.get_messages.call_args.kwargs
        cutoff = call_kwargs["received_after"]
        expected = datetime.now(timezone.utc) - timedelta(hours=48)
        assert abs((cutoff - expected).total_seconds()) < 5
