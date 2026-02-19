from __future__ import annotations

import paho.mqtt.client as mqtt
from loguru import logger

from app.config import get_settings


class MQTTClientManager:
    """Singleton manager for MQTT client connection lifecycle."""

    _instance: MQTTClientManager | None = None

    def __init__(self):
        self._client: mqtt.Client | None = None
        self._connected: bool = False
        self._subscriptions: set[str] = set()

    @classmethod
    def get_instance(cls) -> MQTTClientManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self) -> None:
        settings = get_settings()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.MQTT_CLIENT_ID,
        )

        if settings.MQTT_USERNAME:
            self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_subscribe = self._on_subscribe

        self._client.connect(
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
            settings.MQTT_KEEPALIVE,
        )
        self._client.loop_start()

    def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False

    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        if not self._client or not self._connected:
            raise RuntimeError("MQTT client is not connected")
        result = self._client.publish(topic, payload, qos=qos)
        result.wait_for_publish(timeout=5)

    def subscribe(self, topic: str, qos: int = 1) -> None:
        if not self._client or not self._connected:
            raise RuntimeError("MQTT client is not connected")
        self._client.subscribe(topic, qos=qos)
        self._subscriptions.add(topic)
        logger.info(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str) -> None:
        if not self._client or not self._connected:
            raise RuntimeError("MQTT client is not connected")
        self._client.unsubscribe(topic)
        self._subscriptions.discard(topic)
        logger.info(f"Unsubscribed from topic: {topic}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscriptions(self) -> list[str]:
        return sorted(self._subscriptions)

    # --- Callbacks ---

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            logger.info("MQTT client connected to broker")
            # Re-subscribe on reconnect
            for topic in self._subscriptions:
                client.subscribe(topic)
        else:
            logger.error(f"MQTT connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        if reason_code != 0:
            logger.warning(f"MQTT unexpected disconnect: {reason_code}")
        else:
            logger.info("MQTT client disconnected")

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        logger.info(f"MQTT subscription confirmed (mid={mid}): {reason_code_list}")

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")
        logger.info(f"MQTT message received: {topic} -> {payload[:100]}")

        try:
            from app.services.MQTTService import MQTTService
            service = MQTTService()
            service.handle_message(topic=topic, payload=payload, qos=msg.qos)
        except Exception as e:
            logger.error(f"Failed to handle MQTT message on {topic}: {e}")
