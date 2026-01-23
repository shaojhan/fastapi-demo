from ..exceptions.BaseException import BaseException

class UserException(BaseException):
    """User exception error"""
    
    def __init__(self, message: str | None = None, name: str | None = "User"):
        super().__init__(message=message, name=name)

class UserNotFoundError(UserException):
    """Database returns nothing"""
    status_code = 404
    default_message = 'The user was not found.'

class UserHasAlreadyExistedError(UserException):
    """Database already has the data"""
    status_code = 409
    default_message = 'The user has already existed!'

class PasswordError(UserException):
    """Password should be at least 8 characters and include at least 1 digit and uppercase character"""
    status_code = 403
    default_message = 'Password should be at least 8 characters and include at least 1 digit and uppercase character'


class AuthenticationError(UserException):
    """Invalid credentials - wrong username or password"""
    status_code = 401
    default_message = 'Invalid credentials'


class InvalidTokenError(UserException):
    """Invalid or expired JWT token"""
    status_code = 401
    default_message = 'Invalid or expired token'