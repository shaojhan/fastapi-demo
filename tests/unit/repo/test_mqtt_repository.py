"""
Unit tests for MQTTMessageRepository.
Tests the data access layer for MQTT message persistence.

測試策略:
- 使用 SQLite in-memory 資料庫進行真實 ORM 操作
- 驗證訊息的新增和查詢（含主題過濾、分頁）
"""
import pytest
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.MQTTRepository import MQTTMessageRepository
from app.domain.MQTTModel import MQTTMessageModel


class TestMQTTMessageRepository:
    """測試 MQTTMessageRepository 的 CRUD 操作"""

    def test_add_message(self, test_db_session: Session):
        """測試新增 MQTT 訊息"""
        repo = MQTTMessageRepository(test_db_session)
        msg = MQTTMessageModel.create(
            topic="sensor/temperature",
            payload='{"temp": 25.5}',
            qos=1,
        )

        result = repo.add(msg)
        test_db_session.commit()

        assert result.id is not None
        assert result.topic == "sensor/temperature"
        assert result.payload == '{"temp": 25.5}'
        assert result.qos == 1

    def test_add_message_default_qos(self, test_db_session: Session):
        """測試新增使用預設 QoS 的訊息"""
        repo = MQTTMessageRepository(test_db_session)
        msg = MQTTMessageModel.create(topic="test/topic", payload="hello")

        result = repo.add(msg)
        test_db_session.commit()

        assert result.qos == 0

    def test_get_messages_all(self, test_db_session: Session):
        """測試取得所有訊息"""
        repo = MQTTMessageRepository(test_db_session)
        for i in range(3):
            repo.add(MQTTMessageModel.create(topic=f"topic/{i}", payload=f"msg-{i}"))
        test_db_session.commit()

        messages, total = repo.get_messages()

        assert total == 3
        assert len(messages) == 3

    def test_get_messages_by_topic(self, test_db_session: Session):
        """測試依主題過濾訊息"""
        repo = MQTTMessageRepository(test_db_session)
        for i in range(3):
            repo.add(MQTTMessageModel.create(topic="sensor/temp", payload=f"{i}"))
        repo.add(MQTTMessageModel.create(topic="sensor/humidity", payload="50"))
        test_db_session.commit()

        messages, total = repo.get_messages(topic="sensor/temp")

        assert total == 3
        assert all(m.topic == "sensor/temp" for m in messages)

    def test_get_messages_pagination(self, test_db_session: Session):
        """測試分頁查詢"""
        repo = MQTTMessageRepository(test_db_session)
        for i in range(5):
            repo.add(MQTTMessageModel.create(topic="topic", payload=f"msg-{i}"))
        test_db_session.commit()

        page1, total = repo.get_messages(page=1, size=2)
        assert total == 5
        assert len(page1) == 2

        page2, _ = repo.get_messages(page=2, size=2)
        assert len(page2) == 2

    def test_get_messages_empty(self, test_db_session: Session):
        """測試沒有訊息時的結果"""
        repo = MQTTMessageRepository(test_db_session)
        messages, total = repo.get_messages()
        assert total == 0
        assert len(messages) == 0
