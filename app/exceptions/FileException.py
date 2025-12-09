from ..exceptions.BaseException import BaseException

class FileException(BaseException):
    """File exception error"""
    
    def __init__(self, message: str | None = None, name: str | None = "File"):
        super().__init__(message=message, name=name)

class DataNotFoundError(FileException):
    """Database returns nothing"""
    status_code = 404
    default_message = 'The workflow was not found.'


class AuthenticationError(FileException):
    """invalid """