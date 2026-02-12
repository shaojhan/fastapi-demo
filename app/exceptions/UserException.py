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
    """Invalid JWT token (malformed, bad signature, etc.)"""
    status_code = 401
    error_code = 'INVALID_TOKEN'
    default_message = 'Invalid token'


class TokenExpiredError(UserException):
    """JWT token has expired - client should logout and re-authenticate"""
    status_code = 401
    error_code = 'TOKEN_EXPIRED'
    default_message = 'Token has expired'


class ForbiddenError(UserException):
    """User does not have sufficient permissions"""
    status_code = 403
    default_message = 'You do not have permission to perform this action.'


class EmailNotVerifiedError(UserException):
    """User has not verified their email"""
    status_code = 403
    default_message = 'Please verify your email before logging in.'


class VerificationTokenExpiredError(UserException):
    """Verification token is expired or invalid"""
    status_code = 400
    default_message = 'Verification token has expired or is invalid.'


class EmailAlreadyVerifiedError(UserException):
    """Email has already been verified"""
    status_code = 409
    default_message = 'Email has already been verified.'


class PasswordResetTokenExpiredError(UserException):
    """Password reset token is expired or invalid"""
    status_code = 400
    default_message = 'Password reset token has expired or is invalid.'


class EmailAlreadyRegisteredError(UserException):
    """Email has already been registered"""
    status_code = 409
    default_message = 'This email is already registered.'


class EmailNotVerifiedYetError(UserException):
    """Email is registered but not verified - should resend verification"""
    status_code = 409
    default_message = 'This email is already registered but not verified. Please use resend verification to get a new verification email.'