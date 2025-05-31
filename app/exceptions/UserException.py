from ..exceptions.BaseException import BaseException

class UserException(BaseException):
    """User exception error"""
    
    def __init__(self, message: str | None = None, name: str | None = "User"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class UserNotFountError(UserException):
    """Database returns nothing"""
    status_code = 404
    default_message = 'The user was not found.'

class UserHasAlreadyExistedError(UserException):
    """Database already has the data"""
    status_code = 409
    default_message = 'The user has already existed!'

class PasswordError(UserException):
    """Password should less then 8 and include at least 1 digit character and uppercase character"""
    status_code = 403
    default_message = 'Password should less then 8 and include at least 1 digit character and uppercase characte'


class AuthenticationError(UserException):
    """invalid """