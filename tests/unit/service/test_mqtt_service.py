"""
Unit tests for MQTTService.
Tests the application service layer for MQTT message handling.

測試策略:
- Mock MQTTUnitOfWork 驗證訊息儲存
- Mock MQTTClientManager 驗證發布/訂閱操作
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.MQTTService import MQTTService


def _setup_uow_mock(mock_uow_class):
    mock_uow = MagicMock()
    mock_uow.repo = MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow
    return mock_uow


class TestMQTTServiceHandleMessage:
    """測試 MQTTService.handle_message 訊息儲存"""

    @patch("app.services.MQTTService.MQTTUnitOfWork")
    def test_handle_message_stores_in_db(self, mock_uow_class):
        """測試接收到的訊息被儲存到資料庫"""
        mock_uow = _setup_uow_mock(mock_uow_class)

        service = MQTTService()
        service.handle_message(topic="sensor/temp", payload='{"temp": 25}', qos=1)

        mock_uow.repo.add.assert_called_once()
        mock_uow.commit.assert_called_once()

    @patch("app.services.MQTTService.MQTTUnitOfWork")
    def test_handle_message_creates_domain_model(self, mock_uow_class):
        """測試訊息被正確轉換為領域模型"""
        mock_uow = _setup_uow_mock(mock_uow_class)

        service = MQTTService()
        service.handle_message(topic="test/topic", payload="hello")

        msg = mock_uow.repo.add.call_args[0][0]
        assert msg.topic == "test/topic"
        assert msg.payload == "hello"
        assert msg.qos == 0  # default


class TestMQTTServiceGetMessages:
    """測試 MQTTService.get_messages 查詢"""

    @patch("app.services.MQTTService.MQTTUnitOfWork")
    def test_get_messages_delegates_to_repo(self, mock_uow_class):
        """測試查詢委派給 repository"""
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_messages.return_value = ([], 0)

        service = MQTTService()
        messages, total = service.get_messages(topic="sensor/temp", page=1, size=20)

        mock_uow.repo.get_messages.assert_called_once_with(topic="sensor/temp", page=1, size=20)


class TestMQTTServicePublish:
    """測試 MQTTService.publish 發布"""

    @patch("app.services.MQTTService.MQTTClientManager")
    def test_publish_delegates_to_manager(self, mock_manager_class):
        """測試發布訊息委派給 MQTTClientManager"""
        mock_manager = MagicMock()
        mock_manager_class.get_instance.return_value = mock_manager

        service = MQTTService()
        service.publish("topic/test", "payload", qos=2)

        mock_manager.publish.assert_called_once_with("topic/test", "payload", 2)


class TestMQTTServiceSubscribe:
    """測試 MQTTService 的訂閱/取消訂閱"""

    @patch("app.services.MQTTService.MQTTClientManager")
    def test_subscribe(self, mock_manager_class):
        """測試訂閱主題"""
        mock_manager = MagicMock()
        mock_manager_class.get_instance.return_value = mock_manager

        service = MQTTService()
        service.subscribe("sensor/#", qos=1)

        mock_manager.subscribe.assert_called_once_with("sensor/#", 1)

    @patch("app.services.MQTTService.MQTTClientManager")
    def test_unsubscribe(self, mock_manager_class):
        """測試取消訂閱"""
        mock_manager = MagicMock()
        mock_manager_class.get_instance.return_value = mock_manager

        service = MQTTService()
        service.unsubscribe("sensor/#")

        mock_manager.unsubscribe.assert_called_once_with("sensor/#")


class TestMQTTServiceStatus:
    """測試 MQTTService.get_status"""

    @patch("app.services.MQTTService.MQTTClientManager")
    def test_get_status(self, mock_manager_class):
        """測試取得連線狀態"""
        mock_manager = MagicMock()
        mock_manager.is_connected = True
        mock_manager.subscriptions = ["sensor/temp", "sensor/humidity"]
        mock_manager_class.get_instance.return_value = mock_manager

        service = MQTTService()
        status = service.get_status()

        assert status["connected"] is True
        assert len(status["subscriptions"]) == 2
