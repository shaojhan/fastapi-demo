"""
Unit tests for token verification functionality.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import jwt

from app.utils.token_generator import (
    verify_token,
    generate_token,
    TokenStatus,
    TokenVerificationResult,
    TOKEN_EXPIRY_SECONDS,
)
from app.config import get_settings


settings = get_settings()


class TestTokenVerificationResult:
    """Tests for TokenVerificationResult dataclass."""

    def test_valid_result_properties(self):
        """Test properties for a valid token result."""
        result = TokenVerificationResult(
            status=TokenStatus.VALID,
            payload={'sub': 'user123', 'uid': 'testuser'}
        )

        assert result.is_valid is True
        assert result.is_expired is False
        assert result.payload == {'sub': 'user123', 'uid': 'testuser'}

    def test_expired_result_properties(self):
        """Test properties for an expired token result."""
        result = TokenVerificationResult(status=TokenStatus.EXPIRED)

        assert result.is_valid is False
        assert result.is_expired is True
        assert result.payload is None

    def test_invalid_result_properties(self):
        """Test properties for an invalid token result."""
        result = TokenVerificationResult(status=TokenStatus.INVALID)

        assert result.is_valid is False
        assert result.is_expired is False
        assert result.payload is None


class TestVerifyToken:
    """Tests for verify_token function."""

    def test_verify_valid_token(self):
        """Test verification of a valid token."""
        token = generate_token(user_id='user123', uid='testuser')

        result = verify_token(token)

        assert result.status == TokenStatus.VALID
        assert result.is_valid is True
        assert result.payload is not None
        assert result.payload['sub'] == 'user123'
        assert result.payload['uid'] == 'testuser'

    def test_verify_expired_token(self):
        """Test verification of an expired token returns EXPIRED status."""
        # Create a token that's already expired
        now = datetime.now(timezone.utc)
        payload = {
            'sub': 'user123',
            'uid': 'testuser',
            'iat': now - timedelta(hours=2),
            'exp': now - timedelta(hours=1),  # Expired 1 hour ago
        }
        expired_token = jwt.encode(payload, settings.JWT_KEY, algorithm='HS256')

        result = verify_token(expired_token)

        assert result.status == TokenStatus.EXPIRED
        assert result.is_expired is True
        assert result.is_valid is False
        assert result.payload is None

    def test_verify_invalid_signature(self):
        """Test verification of a token with invalid signature."""
        # Create a token with a different key
        payload = {
            'sub': 'user123',
            'uid': 'testuser',
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        }
        invalid_token = jwt.encode(payload, 'wrong_key', algorithm='HS256')

        result = verify_token(invalid_token)

        assert result.status == TokenStatus.INVALID
        assert result.is_valid is False
        assert result.is_expired is False
        assert result.payload is None

    def test_verify_malformed_token(self):
        """Test verification of a malformed token."""
        result = verify_token('not.a.valid.token')

        assert result.status == TokenStatus.INVALID
        assert result.is_valid is False
        assert result.payload is None

    def test_verify_empty_token(self):
        """Test verification of an empty token."""
        result = verify_token('')

        assert result.status == TokenStatus.INVALID
        assert result.is_valid is False


class TestTokenStatus:
    """Tests for TokenStatus enum."""

    def test_status_values(self):
        """Test TokenStatus enum values."""
        assert TokenStatus.VALID.value == 'valid'
        assert TokenStatus.EXPIRED.value == 'expired'
        assert TokenStatus.INVALID.value == 'invalid'
