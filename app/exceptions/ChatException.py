from app.exceptions.BaseException import BaseException


class ChatException(BaseException):
    """Chat related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "Chat"):
        super().__init__(message=message, name=name)


class ConversationNotFoundError(ChatException):
    """Conversation not found"""
    status_code = 404
    default_message = 'Conversation not found.'


class ConversationAccessDeniedError(ChatException):
    """No permission to access this conversation"""
    status_code = 403
    default_message = 'You do not have permission to access this conversation.'


class OllamaConnectionError(ChatException):
    """Ollama service unavailable"""
    status_code = 503
    default_message = 'AI service is currently unavailable. Please try again later.'
