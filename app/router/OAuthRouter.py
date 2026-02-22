from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from loguru import logger

from app.config import get_settings
from app.router.schemas.OAuthSchema import OAuthExchangeCodeRequest, OAuthTokenResponse
from app.services.GoogleOAuthService import GoogleOAuthService
from app.services.GitHubOAuthService import GitHubOAuthService

router = APIRouter(prefix='/auth', tags=['oauth'])


def get_google_oauth_service() -> GoogleOAuthService:
    return GoogleOAuthService()


def get_github_oauth_service() -> GitHubOAuthService:
    return GitHubOAuthService()


@router.get('/google/login', operation_id='google_login')
async def google_login(service: GoogleOAuthService = Depends(get_google_oauth_service)):
    """Redirect to Google OAuth2 consent screen."""
    state = service.generate_state()
    url = service.get_authorization_url(state)
    return RedirectResponse(url=url)


@router.get('/google/callback', operation_id='google_callback')
async def google_callback(
    code: str = Query(..., description='Authorization code from Google'),
    state: str = Query(..., description='CSRF state token'),
    service: GoogleOAuthService = Depends(get_google_oauth_service),
):
    """Handle Google OAuth2 callback. Redirects to frontend with a short-lived authorization code."""
    settings = get_settings()

    if not service.verify_state(state):
        logger.warning("Google OAuth callback: invalid or expired state token")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error=invalid_state&provider=google",
            status_code=302,
        )

    try:
        token_data = await service.exchange_code(code)
        google_user = await service.get_google_user_info(token_data["access_token"])
        auth_token, user = service.authenticate_google_user(google_user)
        auth_code = service.create_auth_code(auth_token, user)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?code={auth_code}&provider=google",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error=oauth_failed&provider=google",
            status_code=302,
        )


@router.post('/google/token', response_model=OAuthTokenResponse, operation_id='google_exchange_code')
async def exchange_code(
    request_body: OAuthExchangeCodeRequest,
    service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> OAuthTokenResponse:
    """Exchange a short-lived authorization code for an access token."""
    token, user = service.exchange_auth_code(request_body.code)
    return OAuthTokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
    )


# ── GitHub OAuth2 ──────────────────────────────────────────────

@router.get('/github/login', operation_id='github_login')
async def github_login(service: GitHubOAuthService = Depends(get_github_oauth_service)):
    """Redirect to GitHub OAuth2 consent screen."""
    state = service.generate_state()
    url = service.get_authorization_url(state)
    return RedirectResponse(url=url)


@router.get('/github/callback', operation_id='github_callback')
async def github_callback(
    code: str = Query(..., description='Authorization code from GitHub'),
    state: str = Query(..., description='CSRF state token'),
    service: GitHubOAuthService = Depends(get_github_oauth_service),
):
    """Handle GitHub OAuth2 callback. Redirects to frontend with a short-lived authorization code."""
    settings = get_settings()

    if not service.verify_state(state):
        logger.warning("GitHub OAuth callback: invalid or expired state token")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error=invalid_state&provider=github",
            status_code=302,
        )

    try:
        token_data = await service.exchange_code(code)
        github_user = await service.get_github_user_info(token_data["access_token"])
        auth_token, user = service.authenticate_github_user(github_user)
        auth_code = service.create_auth_code(auth_token, user)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?code={auth_code}&provider=github",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error=oauth_failed&provider=github",
            status_code=302,
        )


@router.post('/github/token', response_model=OAuthTokenResponse, operation_id='github_exchange_code')
async def github_exchange_code(
    request_body: OAuthExchangeCodeRequest,
    service: GitHubOAuthService = Depends(get_github_oauth_service),
) -> OAuthTokenResponse:
    """Exchange a short-lived authorization code for an access token."""
    token, user = service.exchange_auth_code(request_body.code)
    return OAuthTokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
    )
