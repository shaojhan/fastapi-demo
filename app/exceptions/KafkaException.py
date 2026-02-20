from app.exceptions.BaseException import BaseException


class KafkaException(BaseException):
    """Kafka related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "Kafka"):
        super().__init__(message=message, name=name)


class KafkaNotRunningError(KafkaException):
    """Kafka client is not running"""
    status_code = 503
    default_message = 'Kafka client is not running.'


class KafkaProduceError(KafkaException):
    """Failed to produce Kafka message"""
    status_code = 500
    default_message = 'Failed to produce Kafka message.'
