from app.exceptions.BaseException import BaseException


class MQTTException(BaseException):
    """MQTT related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "MQTT"):
        super().__init__(message=message, name=name)


class MQTTConnectionError(MQTTException):
    """Failed to connect to MQTT broker"""
    status_code = 503
    default_message = 'Failed to connect to MQTT broker.'


class MQTTNotConnectedError(MQTTException):
    """MQTT client is not connected"""
    status_code = 503
    default_message = 'MQTT client is not connected.'


class MQTTPublishError(MQTTException):
    """Failed to publish MQTT message"""
    status_code = 500
    default_message = 'Failed to publish MQTT message.'
