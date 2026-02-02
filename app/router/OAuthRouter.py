from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from uuid import UUID

from app.router.schemas.UserSchema import LoginResponse, LoginUserInfo
from app.services.GoogleOAuthService import GoogleOAuthService

router = APIRouter(prefix='/auth', tags=['oauth'])


def get_google_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService()


@router.get('/google/login', operation_id='google_login')
async def google_login():
    """Redirect to Google OAuth2 consent screen."""
    service = get_google_oauth_service()
    url = service.get_authorization_url()
    return RedirectResponse(url=url)


@router.get('/google/callback', response_model=LoginResponse, operation_id='google_callback')
async def google_callback(
    code: str = Query(..., description='Authorization code from Google'),
):
    """Handle Google OAuth2 callback. Exchanges code for token and creates/logs in user."""
    service = get_google_oauth_service()

    token_data = await service.exchange_code(code)
    google_user = await service.get_google_user_info(token_data["access_token"])

    auth_token, user = service.authenticate_google_user(google_user)

    return LoginResponse(
        access_token=auth_token.access_token,
        token_type=auth_token.token_type,
        expires_in=auth_token.expires_in,
        user=LoginUserInfo(
            id=UUID(user.id),
            uid=user.uid,
            email=user.email,
            role=user.role,
        ),
    )
