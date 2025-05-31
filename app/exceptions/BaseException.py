class BaseException(Exception):
    """Base exception class"""
    status_code: int = 400
    default_message: str = "Unexpected error occured!"
    
    def __init__(self, message: str | None = None, name: str | None = None):
        self.message = message or self.default_message
        self.name = name
        super().__init__(self.message, self.name)

class DatabaseException(BaseException):
    """Database connection error exception class"""
    status_code = 500
    default_message = 'Can not connect to the database'