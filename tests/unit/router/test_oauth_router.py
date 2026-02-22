"""
Unit tests for OAuthRouter endpoints.
Tests HTTP layer for Google and GitHub OAuth flows.

測試策略:
- TestClient + dependency_overrides
- 驗證 OAuth login 重導向 URL
- 驗證 token exchange 端點
"""
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.OAuthRouter import router
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.domain.services.AuthenticationService import AuthToken
from app.exceptions.BaseException import BaseException as AppBaseException


def _create_app():
    app = FastAPI()

    @app.exception_handler(AppBaseException)
    async def handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router)
    return app


def _make_user():
    return UserModel.reconstitute(
        id="11111111-1111-1111-1111-111111111111", uid="user", email="user@example.com",
        hashed_password="hashed", profile=DomainProfile(name="User"),
        role=UserRole.NORMAL, email_verified=True,
    )


class TestGoogleLogin:
    """測試 GET /auth/google/login 端點"""

    def test_google_login_redirects(self):
        """login 端點應呼叫 generate_state() 並重導向至 Google"""
        from app.router.OAuthRouter import get_google_oauth_service
        app = _create_app()
        mock_service = MagicMock()
        mock_service.generate_state.return_value = "test-state-abc"
        mock_service.get_authorization_url.return_value = "https://accounts.google.com/o/oauth2/v2/auth?state=test-state-abc"

        app.dependency_overrides[get_google_oauth_service] = lambda: mock_service
        client = TestClient(app, follow_redirects=False)

        response = client.get("/auth/google/login")
        assert response.status_code == 307
        assert "accounts.google.com" in response.headers.get("location", "")
        mock_service.generate_state.assert_called_once()
        mock_service.get_authorization_url.assert_called_once_with("test-state-abc")


class TestGoogleCallback:
    """測試 GET /auth/google/callback 端點的 state 驗證"""

    def test_callback_missing_state_returns_422(self):
        """callback 缺少 state 參數應回傳 422"""
        from app.router.OAuthRouter import get_google_oauth_service
        app = _create_app()
        mock_service = MagicMock()
        app.dependency_overrides[get_google_oauth_service] = lambda: mock_service
        client = TestClient(app, follow_redirects=False)

        response = client.get("/auth/google/callback?code=some-code")
        assert response.status_code == 422

    def test_callback_invalid_state_redirects_to_error(self):
        """callback 傳入無效 state 應重導向至 error=invalid_state"""
        from app.router.OAuthRouter import get_google_oauth_service
        from unittest.mock import patch
        app = _create_app()
        mock_service = MagicMock()
        mock_service.verify_state.return_value = False

        app.dependency_overrides[get_google_oauth_service] = lambda: mock_service
        client = TestClient(app, follow_redirects=False)

        with patch("app.router.OAuthRouter.get_settings") as mock_settings:
            mock_settings.return_value.FRONTEND_URL = "http://localhost:3000"
            response = client.get("/auth/google/callback?code=some-code&state=bad-state")

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "error=invalid_state" in location
        assert "provider=google" in location


class TestGitHubLogin:
    """測試 GET /auth/github/login 端點"""

    def test_github_login_redirects(self):
        """login 端點應呼叫 generate_state() 並重導向至 GitHub"""
        from app.router.OAuthRouter import get_github_oauth_service
        app = _create_app()
        mock_service = MagicMock()
        mock_service.generate_state.return_value = "test-state-xyz"
        mock_service.get_authorization_url.return_value = "https://github.com/login/oauth/authorize?state=test-state-xyz"

        app.dependency_overrides[get_github_oauth_service] = lambda: mock_service
        client = TestClient(app, follow_redirects=False)

        response = client.get("/auth/github/login")
        assert response.status_code == 307
        assert "github.com" in response.headers.get("location", "")
        mock_service.generate_state.assert_called_once()
        mock_service.get_authorization_url.assert_called_once_with("test-state-xyz")


class TestGitHubCallback:
    """測試 GET /auth/github/callback 端點的 state 驗證"""

    def test_callback_missing_state_returns_422(self):
        """callback 缺少 state 參數應回傳 422"""
        from app.router.OAuthRouter import get_github_oauth_service
        app = _create_app()
        mock_service = MagicMock()
        app.dependency_overrides[get_github_oauth_service] = lambda: mock_service
        client = TestClient(app, follow_redirects=False)

        response = client.get("/auth/github/callback?code=some-code")
        assert response.status_code == 422

    def test_callback_invalid_state_redirects_to_error(self):
        """callback 傳入無效 state 應重導向至 error=invalid_state"""
        from app.router.OAuthRouter import get_github_oauth_service
        from unittest.mock import patch
        app = _create_app()
        mock_service = MagicMock()
        mock_service.verify_state.return_value = False

        app.dependency_overrides[get_github_oauth_service] = lambda: mock_service
        client = TestClient(app, follow_redirects=False)

        with patch("app.router.OAuthRouter.get_settings") as mock_settings:
            mock_settings.return_value.FRONTEND_URL = "http://localhost:3000"
            response = client.get("/auth/github/callback?code=some-code&state=bad-state")

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "error=invalid_state" in location
        assert "provider=github" in location


class TestTokenExchange:
    """測試 POST /auth/*/token 端點"""

    def test_google_token_exchange(self):
        from app.router.OAuthRouter import get_google_oauth_service
        app = _create_app()
        mock_service = MagicMock()
        token = AuthToken(access_token="google_jwt", token_type="bearer")
        user = _make_user()
        mock_service.exchange_auth_code.return_value = (token, user)

        app.dependency_overrides[get_google_oauth_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/auth/google/token", json={"code": "auth-code-123"})
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "google_jwt"

    def test_github_token_exchange(self):
        from app.router.OAuthRouter import get_github_oauth_service
        app = _create_app()
        mock_service = MagicMock()
        token = AuthToken(access_token="github_jwt", token_type="bearer")
        user = _make_user()
        mock_service.exchange_auth_code.return_value = (token, user)

        app.dependency_overrides[get_github_oauth_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/auth/github/token", json={"code": "auth-code-456"})
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "github_jwt"
