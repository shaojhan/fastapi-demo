"""
Unit tests for GoogleOAuthService authorization code flow.
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.services.GoogleOAuthService import GoogleOAuthService, _oauth_states
from app.domain.UserModel import UserModel, UserRole
from app.domain.services.AuthenticationService import AuthToken


TEST_USER_ID = str(uuid4())


def _make_user() -> UserModel:
    from app.domain.UserModel import Profile, HashedPassword
    return UserModel(
        id=TEST_USER_ID,
        uid="testuser",
        email="test@example.com",
        hashed_password=HashedPassword("hashed"),
        profile=Profile(name="Test User"),
        role=UserRole.NORMAL,
        email_verified=True,
    )


def _make_token() -> AuthToken:
    return AuthToken(access_token="jwt-token", token_type="bearer", expires_in=3600)


class TestGoogleOAuthAuthCodeFlow:
    """Tests for GoogleOAuthService auth code create and exchange."""

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_create_and_exchange_code(self, mock_settings):
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        user = _make_user()
        token = _make_token()

        code = service.create_auth_code(token, user)
        assert isinstance(code, str)
        assert len(code) > 0

        returned_token, returned_user = service.exchange_auth_code(code)
        assert returned_token.access_token == "jwt-token"
        assert returned_user.id == user.id

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_exchange_invalid_code(self, mock_settings):
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()

        with pytest.raises(ValueError, match="Invalid or expired"):
            service.exchange_auth_code("nonexistent-code")

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_exchange_code_only_once(self, mock_settings):
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        user = _make_user()
        token = _make_token()

        code = service.create_auth_code(token, user)
        service.exchange_auth_code(code)

        with pytest.raises(ValueError, match="Invalid or expired"):
            service.exchange_auth_code(code)

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_exchange_expired_code(self, mock_settings):
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        user = _make_user()
        token = _make_token()

        code = service.create_auth_code(token, user)

        from app.services.GoogleOAuthService import _auth_codes
        _auth_codes[code]["created_at"] = time.time() - 120

        with pytest.raises(ValueError, match="expired"):
            service.exchange_auth_code(code)

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_cleanup_expired_codes(self, mock_settings):
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()

        from app.services.GoogleOAuthService import _auth_codes
        _auth_codes["expired-google-code"] = {
            "token": MagicMock(),
            "user": MagicMock(),
            "created_at": time.time() - 120,
        }

        service._cleanup_expired_codes()
        assert "expired-google-code" not in _auth_codes


class TestStateManagement:
    """測試 Google OAuth CSRF state 管理（generate_state / verify_state）"""

    def setup_method(self):
        _oauth_states.clear()

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_generate_state_returns_nonempty_string(self, mock_settings):
        """generate_state 應回傳非空字串 token 並存入 store"""
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        state = service.generate_state()

        assert isinstance(state, str)
        assert len(state) >= 32
        assert state in _oauth_states

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_verify_state_valid(self, mock_settings):
        """verify_state 對剛產生的 state 應回傳 True"""
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        state = service.generate_state()

        assert service.verify_state(state) is True

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_verify_state_consumes_token(self, mock_settings):
        """verify_state 應消耗 state（不可重複使用）"""
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        state = service.generate_state()

        service.verify_state(state)
        assert state not in _oauth_states
        assert service.verify_state(state) is False

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_verify_state_invalid(self, mock_settings):
        """verify_state 對不存在的 state 應回傳 False"""
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()

        assert service.verify_state("nonexistent-state-token") is False

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_verify_state_expired(self, mock_settings):
        """verify_state 對已過期的 state 應回傳 False"""
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        state = service.generate_state()

        _oauth_states[state] = time.time() - 700

        assert service.verify_state(state) is False

    @patch("app.services.GoogleOAuthService.get_settings")
    def test_generate_state_cleans_up_expired(self, mock_settings):
        """generate_state 應自動清除已過期的 state"""
        mock_settings.return_value = MagicMock()
        service = GoogleOAuthService()
        _oauth_states["stale-state"] = time.time() - 700

        service.generate_state()

        assert "stale-state" not in _oauth_states
