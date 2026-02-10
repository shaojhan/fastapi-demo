from app.exceptions.BaseException import BaseException


class SSOException(BaseException):
    """SSO related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "SSO"):
        super().__init__(message=message, name=name)


class SSOProviderNotFoundError(SSOException):
    """SSO Provider not found"""
    status_code = 404
    default_message = 'SSO Provider not found.'


class SSOProviderSlugExistsError(SSOException):
    """SSO Provider slug already exists"""
    status_code = 409
    default_message = 'An SSO Provider with this slug already exists.'


class SSOProviderNameExistsError(SSOException):
    """SSO Provider name already exists"""
    status_code = 409
    default_message = 'An SSO Provider with this name already exists.'


class SSOProviderInactiveError(SSOException):
    """SSO Provider is inactive"""
    status_code = 400
    default_message = 'This SSO Provider is not active.'


class SSOConfigurationError(SSOException):
    """SSO configuration error"""
    status_code = 400
    default_message = 'SSO configuration is invalid.'


class SSOAuthenticationError(SSOException):
    """SSO authentication failed"""
    status_code = 401
    default_message = 'SSO authentication failed.'


class SSOUserNotAllowedError(SSOException):
    """SSO user auto-creation is disabled and user does not exist"""
    status_code = 403
    default_message = 'Your account does not exist. Please contact an administrator.'


class SSOEnforcedError(SSOException):
    """SSO is enforced, password login is not allowed"""
    status_code = 403
    default_message = 'Password login is disabled. Please use SSO to sign in.'


class SSOCallbackError(SSOException):
    """Error during SSO callback processing"""
    status_code = 400
    default_message = 'Failed to process SSO callback.'


class SSOStateInvalidError(SSOException):
    """Invalid or expired SSO state"""
    status_code = 400
    default_message = 'Invalid or expired SSO state. Please try again.'
