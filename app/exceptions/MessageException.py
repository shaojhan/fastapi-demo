from app.exceptions.BaseException import BaseException


class MessageException(BaseException):
    """Message related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "Message"):
        super().__init__(message=message, name=name)


class MessageNotFoundError(MessageException):
    """Message not found"""
    status_code = 404
    default_message = 'Message not found.'


class MessageAccessDeniedError(MessageException):
    """No permission to access this message"""
    status_code = 403
    default_message = 'You do not have permission to access this message.'


class CannotMessageSelfError(MessageException):
    """Cannot send message to self"""
    status_code = 400
    default_message = 'You cannot send a message to yourself.'


class RecipientNotFoundError(MessageException):
    """Recipient user not found"""
    status_code = 404
    default_message = 'Recipient user not found.'


class MessageAlreadyReadError(MessageException):
    """Message is already read"""
    status_code = 400
    default_message = 'Message is already marked as read.'
