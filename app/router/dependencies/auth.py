from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.services.AuthService import AuthService
from app.domain.UserModel import UserModel, UserRole
from app.exceptions.UserException import ForbiddenError


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
        TokenExpiredError: If token has expired (client should logout)
        InvalidTokenError: If token is invalid
    """
    return auth_service.get_current_user(token)


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


def require_employee(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    FastAPI dependency that verifies the current user is an employee or admin.

    Raises:
        ForbiddenError: If user is not an employee or admin
    """
    if current_user.role not in [UserRole.EMPLOYEE, UserRole.ADMIN]:
        raise ForbiddenError(message="Only employees can access this feature")
    return current_user
