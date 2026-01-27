from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.services.AuthService import AuthService
from app.domain.UserModel import UserModel, UserRole
from app.exceptions.UserException import InvalidTokenError, ForbiddenError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


def get_auth_service() -> AuthService:
    return AuthService()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserModel:
    """
    FastAPI dependency that extracts the Bearer token from the Authorization
    header and returns the authenticated user.

    Raises:
        InvalidTokenError: If token is missing, invalid, or expired
    """
    user = auth_service.get_current_user(token)
    if not user:
        raise InvalidTokenError()
    return user


def require_admin(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    FastAPI dependency that verifies the current user has ADMIN role.

    Raises:
        ForbiddenError: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(message="Only administrators can perform this action")
    return current_user
