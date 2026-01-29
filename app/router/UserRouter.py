from fastapi import APIRouter, Depends, Query
from fastapi.security import OAuth2PasswordRequestForm
from uuid import UUID

from app.router.schemas.UserSchema import (
    UserSchema,
    UserRead,
    LoginResponse,
    LoginUserInfo,
    UpdateProfileRequest,
    UpdatePasswordRequest,
    CurrentUserResponse,
    CurrentUserProfileResponse,
    ResendVerificationRequest,
)
from app.services.UserService import UserService
from app.services.AuthService import AuthService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import get_current_user


router = APIRouter(prefix='/users', tags=['user'])


def get_user_service() -> UserService:
    return UserService()


def get_auth_service() -> AuthService:
    return AuthService()


@router.get('/me', response_model=CurrentUserResponse, operation_id='get_current_user')
async def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> CurrentUserResponse:
    """Get the currently authenticated user's information."""
    return CurrentUserResponse(
        id=current_user.id,
        uid=current_user.uid,
        email=current_user.email,
        role=current_user.role,
        profile=CurrentUserProfileResponse(
            name=current_user.profile.name,
            birthdate=current_user.profile.birthdate,
            description=current_user.profile.description,
        )
    )


@router.post('/create', operation_id='create_user')
async def create_user(
    request_body: UserSchema,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user with profile. A verification email will be sent."""
    user_service.add_user_profile(request_body)
    await user_service.send_pending_verification_email()
    return {"message": "User created successfully. Please check your email to verify your account."}


@router.post('/login', response_model=LoginResponse, operation_id='login_user')
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user and return JWT token.
    Accepts uid or email as username, plus password.
    """
    token, user = auth_service.login(
        username=form_data.username,
        password=form_data.password
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


@router.get('/verify-email', operation_id='verify_email')
async def verify_email(
    token: str = Query(..., description='驗證 token'),
    user_service: UserService = Depends(get_user_service)
):
    """Verify user email with token from verification email."""
    user_service.verify_email(token)
    return {"message": "Email verified successfully. You can now log in."}


@router.post('/resend-verification', operation_id='resend_verification')
async def resend_verification(
    request_body: ResendVerificationRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Resend verification email."""
    from app.services.EmailService import EmailService
    token = user_service.resend_verification_email(request_body.email)
    email_service = EmailService()
    await email_service.send_verification_email(request_body.email, token)
    return {"message": "Verification email sent."}


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


