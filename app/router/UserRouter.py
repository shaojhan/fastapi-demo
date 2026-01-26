from fastapi import APIRouter, Depends
from uuid import UUID

from app.router.schemas.UserSchema import (
    UserSchema,
    UserRead,
    LoginRequest,
    LoginResponse,
    LoginUserInfo,
    UpdateProfileRequest,
    UpdatePasswordRequest
)
from app.services.UserService import UserService
from app.services.AuthService import AuthService


router = APIRouter(prefix='/users', tags=['user'])


def get_user_service() -> UserService:
    return UserService()


def get_auth_service() -> AuthService:
    return AuthService()


@router.post('/create', operation_id='create_user')
async def create_user(
    request_body: UserSchema,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user with profile."""
    user = user_service.add_user_profile(request_body)
    return user


@router.post('/login', response_model=LoginResponse, operation_id='login_user')
async def login_user(
    request_body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user and return JWT token.

    Args:
        request_body: Login credentials (uid and password)
        auth_service: Authentication service

    Returns:
        LoginResponse with access token and user info

    Raises:
        AuthenticationError: If credentials are invalid (401)
    """
    token, user = auth_service.login(
        uid=request_body.uid,
        password=request_body.password
    )

    user_info = LoginUserInfo(
        id=UUID(user.id),
        uid=user.uid,
        email=user.email,
        role=user.role
    )

    return LoginResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=user_info
    )


@router.post('/update', operation_id='update_password')
async def update_password(
    request_body: UpdatePasswordRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Update user password."""
    user_service.update_password(
        user_id=str(request_body.user_id),
        old_password=request_body.old_password,
        new_password=request_body.new_password
    )
    return {"message": "Password updated successfully"}


@router.post('/profile/create', operation_id='create_user_profile')
async def create_user_profile(request_body):
    """Create user profile."""
    return request_body


@router.post('/profile/update', operation_id='update_user_profile')
async def update_user_profile(
    request_body: UpdateProfileRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Update user profile."""
    return user_service.update_user_profile(
        user_id=str(request_body.user_id),
        name=request_body.name,
        birthdate=request_body.birthdate,
        description=request_body.description
    )


@router.post('/create-session', operation_id='create_user_session')
async def create_user_session(request_body):
    """Create user session."""
    return request_body
