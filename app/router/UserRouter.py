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
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserListResponse,
    UserListItem,
    UserSearchResponse,
    UserSearchItem,
)
from app.services.UserService import UserService, UserQueryService
from app.services.AuthService import AuthService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import get_current_user, require_admin


router = APIRouter(prefix='/users', tags=['user'])


def get_user_service() -> UserService:
    return UserService()


def get_auth_service() -> AuthService:
    return AuthService()


def get_user_query_service() -> UserQueryService:
    return UserQueryService()


@router.get('/', response_model=UserListResponse, operation_id='list_users')
async def list_users(
    page: int = Query(1, ge=1, description='頁碼'),
    size: int = Query(20, ge=1, le=100, description='每頁筆數'),
    admin_user: UserModel = Depends(require_admin),
    query_service: UserQueryService = Depends(get_user_query_service),
) -> UserListResponse:
    """List all users with pagination (Admin only)."""
    users, total = query_service.get_all_users(page, size)
    items = [
        UserListItem(
            id=u.id,
            uid=u.uid,
            email=u.email,
            role=u.role,
            email_verified=u.email_verified,
        )
        for u in users
    ]
    return UserListResponse(items=items, total=total, page=page, size=size)


@router.get('/search', response_model=UserSearchResponse, operation_id='search_users')
async def search_users(
    keyword: str = Query(..., min_length=1, description='搜尋關鍵字（帳號、郵件或姓名）'),
    limit: int = Query(20, ge=1, le=50, description='最大結果數'),
    current_user: UserModel = Depends(get_current_user),
    query_service: UserQueryService = Depends(get_user_query_service),
) -> UserSearchResponse:
    """Search users by keyword (uid, email, or name). For all logged-in users."""
    users, total = query_service.search_users(
        keyword=keyword,
        exclude_user_id=current_user.id,
        limit=limit
    )
    items = [
        UserSearchItem(
            id=u.id,
            uid=u.uid,
            email=u.email,
            name=u.profile.name if u.profile else None,
        )
        for u in users
    ]
    return UserSearchResponse(items=items, total=total)


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


@router.post('/forgot-password', operation_id='forgot_password')
async def forgot_password(
    request_body: ForgotPasswordRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Send a password reset email."""
    from app.services.EmailService import EmailService
    token = user_service.forgot_password(request_body.email)
    email_service = EmailService()
    await email_service.send_password_reset_email(request_body.email, token)
    return {"message": "Password reset email sent. Please check your inbox."}


@router.post('/reset-password', operation_id='reset_password')
async def reset_password(
    request_body: ResetPasswordRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Reset password using a reset token."""
    user_service.reset_password(
        token=request_body.token,
        new_password=request_body.new_password
    )
    return {"message": "Password has been reset successfully. You can now log in."}


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


