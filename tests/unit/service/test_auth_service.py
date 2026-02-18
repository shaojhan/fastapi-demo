"""
Unit tests for AuthService authentication methods.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import jwt

from app.services.AuthService import AuthService
from app.utils.token_generator import (
    TokenStatus,
    TokenVerificationResult,
    generate_token,
)
from app.exceptions.UserException import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    EmailNotVerifiedError,
)
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.config import get_settings


settings = get_settings()


def _make_user_model(user_id='user123') -> UserModel:
    """Create a test user model."""
    return UserModel.reconstitute(
        id=user_id,
        uid='testuser',
        email='test@example.com',
        hashed_password='hashed',
        profile=DomainProfile(name='Test User', birthdate=None, description=None),
        role=UserRole.NORMAL,
        email_verified=True,
    )


class TestAuthServiceGetCurrentUser:
    """Tests for AuthService.get_current_user method."""

    @patch('app.services.AuthService.UserUnitOfWork')
    def test_get_current_user_valid_token(self, mock_uow_class):
        """Test get_current_user returns user for valid token."""
        # Arrange
        user = _make_user_model()
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = user

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        token = generate_token(user_id='user123', uid='testuser')

        # Act
        service = AuthService()
        result = service.get_current_user(token)

        # Assert
        assert result == user
        mock_repo.get_by_id.assert_called_once_with('user123')

    def test_get_current_user_expired_token_raises(self):
        """Test get_current_user raises TokenExpiredError for expired token."""
        # Arrange
        now = datetime.now(timezone.utc)
        payload = {
            'sub': 'user123',
            'uid': 'testuser',
            'iat': now - timedelta(hours=2),
            'exp': now - timedelta(hours=1),  # Expired
        }
        expired_token = jwt.encode(payload, settings.JWT_KEY, algorithm='HS256')

        # Act & Assert
        service = AuthService()
        with pytest.raises(TokenExpiredError):
            service.get_current_user(expired_token)

    def test_get_current_user_invalid_token_raises(self):
        """Test get_current_user raises InvalidTokenError for invalid token."""
        # Arrange
        invalid_token = 'not.a.valid.token'

        # Act & Assert
        service = AuthService()
        with pytest.raises(InvalidTokenError):
            service.get_current_user(invalid_token)

    def test_get_current_user_wrong_signature_raises(self):
        """Test get_current_user raises InvalidTokenError for wrong signature."""
        # Arrange
        payload = {
            'sub': 'user123',
            'uid': 'testuser',
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        }
        bad_token = jwt.encode(payload, 'wrong_key', algorithm='HS256')

        # Act & Assert
        service = AuthService()
        with pytest.raises(InvalidTokenError):
            service.get_current_user(bad_token)

    @patch('app.services.AuthService.UserUnitOfWork')
    def test_get_current_user_missing_sub_raises(self, mock_uow_class):
        """Test get_current_user raises InvalidTokenError when sub claim is missing."""
        # Arrange - Create token without 'sub' claim
        now = datetime.now(timezone.utc)
        payload = {
            'uid': 'testuser',
            'iat': now,
            'exp': now + timedelta(hours=1),
        }
        token_without_sub = jwt.encode(payload, settings.JWT_KEY, algorithm='HS256')

        # Act & Assert
        service = AuthService()
        with pytest.raises(InvalidTokenError):
            service.get_current_user(token_without_sub)

    @patch('app.services.AuthService.UserUnitOfWork')
    def test_get_current_user_user_not_found_raises(self, mock_uow_class):
        """Test get_current_user raises InvalidTokenError when user not found."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None  # User not found

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        token = generate_token(user_id='nonexistent', uid='testuser')

        # Act & Assert
        service = AuthService()
        with pytest.raises(InvalidTokenError):
            service.get_current_user(token)


class TestAuthServiceVerifyToken:
    """Tests for AuthService.verify_token method."""

    def test_verify_token_returns_result(self):
        """Test verify_token returns TokenVerificationResult."""
        token = generate_token(user_id='user123', uid='testuser')

        service = AuthService()
        result = service.verify_token(token)

        assert isinstance(result, TokenVerificationResult)
        assert result.is_valid is True


def _make_user_model_for_login(
    user_id='user123',
    email_verified=True,
    role=UserRole.NORMAL,
) -> UserModel:
    """Create a test user model for login tests."""
    return UserModel.reconstitute(
        id=user_id,
        uid='testuser',
        email='test@example.com',
        hashed_password='hashed_correct_password',
        profile=DomainProfile(name='Test User', birthdate=None, description=None),
        role=role,
        email_verified=email_verified,
    )


def _setup_login_uow_mock(mock_uow_class, user=None):
    """Helper to set up UoW mock for login tests."""
    mock_repo = MagicMock()
    mock_repo.get_by_uid.return_value = user
    mock_repo.get_by_email.return_value = None

    mock_uow = MagicMock()
    mock_uow.repo = mock_repo
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow

    return mock_repo


def _setup_sso_uow_mock(mock_sso_uow_class, enforce_sso=False):
    """Helper to set up SSO UoW mock."""
    mock_config = MagicMock()
    mock_config.enforce_sso = enforce_sso

    mock_config_repo = MagicMock()
    mock_config_repo.get_config.return_value = mock_config

    mock_sso_uow = MagicMock()
    mock_sso_uow.config_repo = mock_config_repo
    mock_sso_uow.__enter__ = MagicMock(return_value=mock_sso_uow)
    mock_sso_uow.__exit__ = MagicMock(return_value=False)
    mock_sso_uow_class.return_value = mock_sso_uow


class TestAuthServiceLogin:
    """Tests for AuthService.login method with login recording."""

    @patch('app.services.AuthService.LoginRecordService')
    @patch('app.services.AuthService.SSOQueryUnitOfWork')
    @patch('app.services.AuthService.UserUnitOfWork')
    def test_login_success_records_login(self, mock_uow_class, mock_sso_uow_class, mock_record_svc_class):
        """測試成功登錄會記錄登錄紀錄"""
        user = _make_user_model_for_login()
        _setup_login_uow_mock(mock_uow_class, user)
        _setup_sso_uow_mock(mock_sso_uow_class, enforce_sso=False)

        mock_record_svc = MagicMock()
        mock_record_svc_class.return_value = mock_record_svc

        service = AuthService()
        # Need to patch _verify_password since hashed_password is not real bcrypt
        with patch.object(service, '_verify_password', return_value=True):
            token, result_user = service.login(
                username='testuser',
                password='correct_password',
                ip_address='192.168.1.1',
                user_agent='Mozilla/5.0',
            )

        assert result_user.uid == 'testuser'
        assert token is not None

        # Verify login was recorded as success
        mock_record_svc.record_login.assert_called()
        calls = mock_record_svc.record_login.call_args_list
        success_call = calls[-1]
        assert success_call[1]['success'] is True

    @patch('app.services.AuthService.LoginRecordService')
    @patch('app.services.AuthService.UserUnitOfWork')
    def test_login_user_not_found_records_failure(self, mock_uow_class, mock_record_svc_class):
        """測試帳號不存在時記錄失敗紀錄"""
        _setup_login_uow_mock(mock_uow_class, user=None)

        mock_record_svc = MagicMock()
        mock_record_svc_class.return_value = mock_record_svc

        service = AuthService()
        with pytest.raises(AuthenticationError):
            service.login(
                username='nonexistent',
                password='password',
                ip_address='10.0.0.1',
                user_agent='curl/7.88',
            )

        mock_record_svc.record_login.assert_called_once()
        call_kwargs = mock_record_svc.record_login.call_args[1]
        assert call_kwargs['success'] is False
        assert call_kwargs['username'] == 'nonexistent'
        assert call_kwargs['ip_address'] == '10.0.0.1'
        assert '帳號不存在' in call_kwargs['failure_reason']

    @patch('app.services.AuthService.LoginRecordService')
    @patch('app.services.AuthService.SSOQueryUnitOfWork')
    @patch('app.services.AuthService.UserUnitOfWork')
    def test_login_wrong_password_records_failure(self, mock_uow_class, mock_sso_uow_class, mock_record_svc_class):
        """測試密碼錯誤時記錄失敗紀錄"""
        user = _make_user_model_for_login()
        _setup_login_uow_mock(mock_uow_class, user)
        _setup_sso_uow_mock(mock_sso_uow_class, enforce_sso=False)

        mock_record_svc = MagicMock()
        mock_record_svc_class.return_value = mock_record_svc

        service = AuthService()
        with patch.object(service, '_verify_password', return_value=False):
            with pytest.raises(AuthenticationError):
                service.login(
                    username='testuser',
                    password='wrong_password',
                    ip_address='192.168.1.1',
                    user_agent='Mozilla/5.0',
                )

        mock_record_svc.record_login.assert_called_once()
        call_kwargs = mock_record_svc.record_login.call_args[1]
        assert call_kwargs['success'] is False
        assert call_kwargs['user_id'] == 'user123'
        assert '密碼錯誤' in call_kwargs['failure_reason']

    @patch('app.services.AuthService.LoginRecordService')
    @patch('app.services.AuthService.SSOQueryUnitOfWork')
    @patch('app.services.AuthService.UserUnitOfWork')
    def test_login_email_not_verified_records_failure(self, mock_uow_class, mock_sso_uow_class, mock_record_svc_class):
        """測試 Email 未驗證時記錄失敗紀錄"""
        user = _make_user_model_for_login(email_verified=False)
        _setup_login_uow_mock(mock_uow_class, user)
        _setup_sso_uow_mock(mock_sso_uow_class, enforce_sso=False)

        mock_record_svc = MagicMock()
        mock_record_svc_class.return_value = mock_record_svc

        service = AuthService()
        with patch.object(service, '_verify_password', return_value=True):
            with pytest.raises(EmailNotVerifiedError):
                service.login(
                    username='testuser',
                    password='correct_password',
                    ip_address='192.168.1.1',
                    user_agent='Mozilla/5.0',
                )

        mock_record_svc.record_login.assert_called_once()
        call_kwargs = mock_record_svc.record_login.call_args[1]
        assert call_kwargs['success'] is False
        assert 'Email' in call_kwargs['failure_reason']

    @patch('app.services.AuthService.LoginRecordService')
    @patch('app.services.AuthService.UserUnitOfWork')
    def test_login_record_failure_does_not_prevent_exception(self, mock_uow_class, mock_record_svc_class):
        """測試記錄登錄失敗不影響原本的例外拋出"""
        _setup_login_uow_mock(mock_uow_class, user=None)

        mock_record_svc = MagicMock()
        mock_record_svc.record_login.side_effect = Exception("DB error")
        mock_record_svc_class.return_value = mock_record_svc

        service = AuthService()
        with pytest.raises(AuthenticationError):
            service.login(
                username='nonexistent',
                password='password',
                ip_address='10.0.0.1',
                user_agent='curl/7.88',
            )
