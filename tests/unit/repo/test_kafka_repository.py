"""
Unit tests for KafkaMessageRepository.
Tests the data access layer for Kafka message persistence.

測試策略:
- 使用 SQLite in-memory 資料庫進行真實 ORM 操作
- 驗證訊息的新增和查詢（含主題過濾、分頁）
"""
import pytest
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.KafkaRepository import KafkaMessageRepository
from app.domain.KafkaModel import KafkaMessageModel


class TestKafkaMessageRepository:
    """測試 KafkaMessageRepository 的 CRUD 操作"""

    def test_add_message(self, test_db_session: Session):
        """測試新增 Kafka 訊息"""
        repo = KafkaMessageRepository(test_db_session)
        msg = KafkaMessageModel.create(
            topic="test-topic",
            value='{"key": "value"}',
            key="msg-key",
            partition=0,
            offset=100,
        )

        result = repo.add(msg)
        test_db_session.commit()

        assert result.id is not None
        assert result.topic == "test-topic"
        assert result.value == '{"key": "value"}'
        assert result.key == "msg-key"
        assert result.partition == 0
        assert result.offset == 100

    def test_add_message_without_optional_fields(self, test_db_session: Session):
        """測試新增不含可選欄位的訊息"""
        repo = KafkaMessageRepository(test_db_session)
        msg = KafkaMessageModel.create(topic="simple-topic", value="hello")

        result = repo.add(msg)
        test_db_session.commit()

        assert result.id is not None
        assert result.key is None
        assert result.partition is None
        assert result.offset is None

    def test_get_messages_all(self, test_db_session: Session):
        """測試取得所有訊息"""
        repo = KafkaMessageRepository(test_db_session)
        for i in range(3):
            msg = KafkaMessageModel.create(topic=f"topic-{i}", value=f"value-{i}")
            repo.add(msg)
        test_db_session.commit()

        messages, total = repo.get_messages()

        assert total == 3
        assert len(messages) == 3

    def test_get_messages_by_topic(self, test_db_session: Session):
        """測試依主題過濾訊息"""
        repo = KafkaMessageRepository(test_db_session)
        for i in range(3):
            repo.add(KafkaMessageModel.create(topic="target", value=f"v{i}"))
        repo.add(KafkaMessageModel.create(topic="other", value="other"))
        test_db_session.commit()

        messages, total = repo.get_messages(topic="target")

        assert total == 3
        assert all(m.topic == "target" for m in messages)

    def test_get_messages_pagination(self, test_db_session: Session):
        """測試分頁查詢"""
        repo = KafkaMessageRepository(test_db_session)
        for i in range(5):
            repo.add(KafkaMessageModel.create(topic="topic", value=f"v{i}"))
        test_db_session.commit()

        page1, total = repo.get_messages(page=1, size=2)
        assert total == 5
        assert len(page1) == 2

        page2, _ = repo.get_messages(page=2, size=2)
        assert len(page2) == 2

    def test_get_messages_empty(self, test_db_session: Session):
        """測試沒有訊息時的結果"""
        repo = KafkaMessageRepository(test_db_session)
        messages, total = repo.get_messages()
        assert total == 0
        assert len(messages) == 0
