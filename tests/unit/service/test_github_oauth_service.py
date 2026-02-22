"""
Unit tests for GitHubOAuthService.
Tests the GitHub OAuth2 flow and user authentication.

測試策略:
- Mock httpx.AsyncClient 驗證 API 呼叫
- Mock UserUnitOfWork 驗證使用者查詢和建立
- 驗證 authorization code 的建立和交換
"""
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.GitHubOAuthService import GitHubOAuthService, _auth_codes, _oauth_states
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.domain.services.AuthenticationService import AuthToken


def _make_user(user_id="user-1", github_id=None):
    return UserModel.reconstitute(
        id=user_id,
        uid="testuser",
        email="test@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Test"),
        role=UserRole.NORMAL,
        github_id=github_id,
    )


def _make_auth_token():
    return AuthToken(access_token="jwt_token", token_type="bearer")


def _setup_uow_mock(mock_uow_class, repo_mock=None):
    mock_uow = MagicMock()
    mock_uow.repo = repo_mock or MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow
    return mock_uow


class TestGetAuthorizationUrl:
    """測試 get_authorization_url 方法"""

    def test_returns_github_url(self):
        """測試回傳包含 GitHub OAuth 參數的 URL"""
        service = GitHubOAuthService()
        url = service.get_authorization_url("test-state-value")

        assert "https://github.com/login/oauth/authorize" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "state=test-state-value" in url


class TestStateManagement:
    """測試 OAuth CSRF state 管理（generate_state / verify_state）"""

    def setup_method(self):
        _oauth_states.clear()

    def test_generate_state_returns_nonempty_string(self):
        """generate_state 應回傳非空字串 token"""
        service = GitHubOAuthService()
        state = service.generate_state()

        assert isinstance(state, str)
        assert len(state) >= 32
        assert state in _oauth_states

    def test_verify_state_valid(self):
        """verify_state 對剛產生的 state 應回傳 True"""
        service = GitHubOAuthService()
        state = service.generate_state()

        assert service.verify_state(state) is True

    def test_verify_state_consumes_token(self):
        """verify_state 應消耗 state（不可重複使用）"""
        service = GitHubOAuthService()
        state = service.generate_state()

        service.verify_state(state)
        assert state not in _oauth_states
        assert service.verify_state(state) is False

    def test_verify_state_invalid(self):
        """verify_state 對不存在的 state 應回傳 False"""
        service = GitHubOAuthService()
        assert service.verify_state("nonexistent-state-token") is False

    def test_verify_state_expired(self):
        """verify_state 對已過期的 state 應回傳 False"""
        import time
        service = GitHubOAuthService()
        state = service.generate_state()

        # 手動讓 state 過期
        _oauth_states[state] = time.time() - 700

        assert service.verify_state(state) is False

    def test_generate_state_cleans_up_expired(self):
        """generate_state 應自動清除已過期的 state"""
        import time
        service = GitHubOAuthService()
        _oauth_states["stale-state"] = time.time() - 700

        service.generate_state()

        assert "stale-state" not in _oauth_states


class TestExchangeCode:
    """測試 exchange_code 方法"""

    @pytest.mark.asyncio
    async def test_exchange_code_calls_github_api(self):
        """測試交換授權碼時呼叫 GitHub API"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "token123", "token_type": "bearer"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.GitHubOAuthService.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client

            service = GitHubOAuthService()
            result = await service.exchange_code("auth_code_123")

            assert result["access_token"] == "token123"
            mock_client.post.assert_awaited_once()


class TestAuthenticateGitHubUser:
    """測試 authenticate_github_user 方法"""

    @patch("app.services.GitHubOAuthService.UserUnitOfWork")
    def test_existing_github_user_returns_token(self, mock_uow_class):
        """測試已連結 GitHub 的使用者直接回傳 token"""
        user = _make_user(github_id="123")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_github_id.return_value = user

        service = GitHubOAuthService()
        with patch.object(service, '_auth_domain_service') as mock_auth:
            mock_auth.create_token.return_value = _make_auth_token()
            token, result_user = service.authenticate_github_user({"id": 123, "email": "test@example.com"})

        assert result_user == user
        assert token.access_token == "jwt_token"

    @patch("app.services.GitHubOAuthService.UserUnitOfWork")
    def test_existing_email_links_github_id(self, mock_uow_class):
        """測試 email 已存在的使用者會連結 GitHub 帳號"""
        user = _make_user()
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_github_id.return_value = None
        mock_uow.repo.get_by_email.return_value = user

        service = GitHubOAuthService()
        with patch.object(service, '_auth_domain_service') as mock_auth:
            mock_auth.create_token.return_value = _make_auth_token()
            token, result_user = service.authenticate_github_user(
                {"id": 456, "email": "test@example.com", "login": "ghuser"}
            )

        mock_uow.repo.link_github_id.assert_called_once_with(user.id, "456")
        mock_uow.commit.assert_called()

    @patch("app.services.GitHubOAuthService.UserUnitOfWork")
    def test_new_user_auto_registers(self, mock_uow_class):
        """測試新使用者會自動註冊"""
        new_user = _make_user(github_id="789")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_github_id.side_effect = [None, new_user]  # First call: not found, second: found after creation
        mock_uow.repo.get_by_email.return_value = None
        mock_uow.repo.exists_by_uid.return_value = False

        service = GitHubOAuthService()
        with patch.object(service, '_auth_domain_service') as mock_auth:
            mock_auth.create_token.return_value = _make_auth_token()
            token, result_user = service.authenticate_github_user(
                {"id": 789, "email": "new@example.com", "login": "newghuser", "name": "New User"}
            )

        mock_uow.repo.add.assert_called_once()
        mock_uow.commit.assert_called()

    @patch("app.services.GitHubOAuthService.UserUnitOfWork")
    def test_no_email_raises_error(self, mock_uow_class):
        """測試沒有 email 的 GitHub 帳號會拋出錯誤"""
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_github_id.return_value = None

        service = GitHubOAuthService()
        with pytest.raises(ValueError, match="no associated email"):
            service.authenticate_github_user({"id": 999})


class TestAuthCode:
    """測試 authorization code 的建立和交換"""

    def setup_method(self):
        _auth_codes.clear()

    def test_create_auth_code(self):
        """測試建立 authorization code"""
        service = GitHubOAuthService()
        token = _make_auth_token()
        user = _make_user()
        code = service.create_auth_code(token, user)

        assert isinstance(code, str)
        assert len(code) > 0
        assert code in _auth_codes

    def test_exchange_auth_code_success(self):
        """測試成功交換 authorization code"""
        service = GitHubOAuthService()
        token = _make_auth_token()
        user = _make_user()
        code = service.create_auth_code(token, user)

        result_token, result_user = service.exchange_auth_code(code)

        assert result_token == token
        assert result_user == user
        assert code not in _auth_codes  # Code should be consumed

    def test_exchange_invalid_code_raises(self):
        """測試使用無效 code 會拋出錯誤"""
        service = GitHubOAuthService()
        with pytest.raises(ValueError, match="Invalid or expired"):
            service.exchange_auth_code("invalid-code")

    def test_exchange_expired_code_raises(self):
        """測試使用過期 code 會拋出錯誤"""
        service = GitHubOAuthService()
        token = _make_auth_token()
        user = _make_user()
        code = service.create_auth_code(token, user)

        # Manually expire the code
        _auth_codes[code]["created_at"] = time.time() - 120

        with pytest.raises(ValueError, match="expired"):
            service.exchange_auth_code(code)
