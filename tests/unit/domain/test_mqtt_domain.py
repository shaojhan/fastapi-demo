import pytest
from datetime import datetime, timezone

from app.domain.MQTTModel import MQTTMessageModel


# --- Test Data ---
TEST_TOPIC = "test/hello"
TEST_PAYLOAD = "Hello MQTT"
TEST_QOS = 1


class TestMQTTMessageModelCreation:
    """測試 MQTTMessageModel 建立功能"""

    def test_create_with_valid_data(self):
        """
        測試使用有效資料建立 MQTT 訊息。
        """
        message = MQTTMessageModel.create(
            topic=TEST_TOPIC,
            payload=TEST_PAYLOAD,
            qos=TEST_QOS,
        )

        assert isinstance(message, MQTTMessageModel)
        assert message.topic == TEST_TOPIC
        assert message.payload == TEST_PAYLOAD
        assert message.qos == TEST_QOS
        assert message.id is None
        assert message.received_at is not None

    def test_create_sets_received_at_to_utc_now(self):
        """
        測試建立訊息時 received_at 設為 UTC 時間。
        """
        before = datetime.now(timezone.utc)
        message = MQTTMessageModel.create(topic=TEST_TOPIC, payload=TEST_PAYLOAD)
        after = datetime.now(timezone.utc)

        assert before <= message.received_at <= after

    def test_create_with_default_qos(self):
        """
        測試 QoS 預設值為 0。
        """
        message = MQTTMessageModel.create(topic=TEST_TOPIC, payload=TEST_PAYLOAD)

        assert message.qos == 0

    def test_create_with_empty_topic_raises_error(self):
        """
        測試使用空白主題建立訊息會拋出 ValueError。
        """
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            MQTTMessageModel.create(topic="", payload=TEST_PAYLOAD)

    def test_create_with_empty_payload(self):
        """
        測試使用空白 payload 建立訊息（MQTT 允許空 payload）。
        """
        message = MQTTMessageModel.create(topic=TEST_TOPIC, payload="")

        assert message.payload == ""


class TestMQTTMessageModelReconstitute:
    """測試 MQTTMessageModel reconstitute 工廠方法"""

    def test_reconstitute_creates_message_from_persistence(self):
        """
        測試從持久化資料重建訊息。
        """
        received_at = datetime(2024, 1, 10, 8, 0, 0)

        message = MQTTMessageModel.reconstitute(
            id=42,
            topic=TEST_TOPIC,
            payload=TEST_PAYLOAD,
            qos=TEST_QOS,
            received_at=received_at,
        )

        assert message.id == 42
        assert message.topic == TEST_TOPIC
        assert message.payload == TEST_PAYLOAD
        assert message.qos == TEST_QOS
        assert message.received_at == received_at


class TestMQTTMessageModelProperties:
    """測試 MQTTMessageModel 屬性為唯讀"""

    def test_properties_are_readonly(self):
        """
        測試所有屬性為唯讀。
        """
        message = MQTTMessageModel.create(
            topic=TEST_TOPIC,
            payload=TEST_PAYLOAD,
            qos=TEST_QOS,
        )

        with pytest.raises(AttributeError):
            message.topic = "other/topic"

        with pytest.raises(AttributeError):
            message.payload = "other"

        with pytest.raises(AttributeError):
            message.qos = 2

        with pytest.raises(AttributeError):
            message.received_at = datetime.now(timezone.utc)
