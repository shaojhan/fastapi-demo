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
from app.exceptions.UserException import InvalidTokenError, TokenExpiredError
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
