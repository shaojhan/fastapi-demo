"""
Unit tests for KafkaService.
Tests the application service layer for Kafka message handling.

測試策略:
- Mock KafkaUnitOfWork 驗證訊息儲存
- Mock KafkaClientManager 驗證生產/訂閱操作
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.KafkaService import KafkaService


def _setup_uow_mock(mock_uow_class):
    mock_uow = MagicMock()
    mock_uow.repo = MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow
    return mock_uow


class TestKafkaServiceHandleMessage:
    """測試 KafkaService.handle_message 訊息儲存"""

    @patch("app.services.KafkaService.KafkaUnitOfWork")
    def test_handle_message_stores_in_db(self, mock_uow_class):
        """測試接收到的訊息被儲存到資料庫"""
        mock_uow = _setup_uow_mock(mock_uow_class)

        service = KafkaService()
        service.handle_message(topic="test-topic", value="test-value", key="key-1")

        mock_uow.repo.add.assert_called_once()
        mock_uow.commit.assert_called_once()

    @patch("app.services.KafkaService.KafkaUnitOfWork")
    def test_handle_message_with_all_fields(self, mock_uow_class):
        """測試帶有全部欄位的訊息儲存"""
        mock_uow = _setup_uow_mock(mock_uow_class)

        service = KafkaService()
        service.handle_message(
            topic="topic", value="value", key="key", partition=0, offset=42
        )

        mock_uow.repo.add.assert_called_once()
        msg = mock_uow.repo.add.call_args[0][0]
        assert msg.topic == "topic"
        assert msg.value == "value"
        assert msg.key == "key"


class TestKafkaServiceGetMessages:
    """測試 KafkaService.get_messages 查詢"""

    @patch("app.services.KafkaService.KafkaUnitOfWork")
    def test_get_messages_delegates_to_repo(self, mock_uow_class):
        """測試查詢委派給 repository"""
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_messages.return_value = ([], 0)

        service = KafkaService()
        messages, total = service.get_messages(topic="test", page=2, size=10)

        mock_uow.repo.get_messages.assert_called_once_with(topic="test", page=2, size=10)
        assert total == 0


class TestKafkaServiceProduce:
    """測試 KafkaService.produce 發送"""

    @patch("app.services.KafkaService.KafkaClientManager")
    @pytest.mark.asyncio
    async def test_produce_delegates_to_manager(self, mock_manager_class):
        """測試發送訊息委派給 KafkaClientManager"""
        mock_manager = MagicMock()
        mock_manager.produce = AsyncMock()
        mock_manager_class.get_instance.return_value = mock_manager

        service = KafkaService()
        await service.produce("topic", "value", key="key")

        mock_manager.produce.assert_awaited_once_with("topic", "value", "key")


class TestKafkaServiceStatus:
    """測試 KafkaService.get_status"""

    @patch("app.services.KafkaService.KafkaClientManager")
    def test_get_status(self, mock_manager_class):
        """測試取得連線狀態"""
        mock_manager = MagicMock()
        mock_manager.is_running = True
        mock_manager.subscriptions = ["topic-1"]
        mock_manager_class.get_instance.return_value = mock_manager

        service = KafkaService()
        status = service.get_status()

        assert status["running"] is True
        assert status["subscriptions"] == ["topic-1"]
