import jwt
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional

from app.config import get_settings

settings = get_settings()

# Token expiration time in seconds (1 hour)
TOKEN_EXPIRY_SECONDS = 3600


class TokenStatus(Enum):
    """Token verification status."""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class TokenVerificationResult:
    """Result of token verification."""
    status: TokenStatus
    payload: Optional[dict] = None

    @property
    def is_valid(self) -> bool:
        return self.status == TokenStatus.VALID

    @property
    def is_expired(self) -> bool:
        return self.status == TokenStatus.EXPIRED


def generate_token(user_id: str, uid: str) -> str:
    """
    Generate a JWT token for the given user.

    Args:
        user_id: The user's UUID
        uid: The user's username

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,  # subject - user identifier
        "uid": uid,      # username
        "iat": now,      # issued at
        "exp": now + timedelta(seconds=TOKEN_EXPIRY_SECONDS),  # expiration
    }
    token = jwt.encode(payload, settings.JWT_KEY, algorithm='HS256')
    return token


def verify_token(token: str) -> TokenVerificationResult:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify

    Returns:
        TokenVerificationResult with status and payload
    """
    try:
        decoded_token = jwt.decode(
            token,
            settings.JWT_KEY,
            algorithms=['HS256']
        )
        return TokenVerificationResult(status=TokenStatus.VALID, payload=decoded_token)
    except jwt.ExpiredSignatureError:
        return TokenVerificationResult(status=TokenStatus.EXPIRED)
    except jwt.InvalidTokenError:
        return TokenVerificationResult(status=TokenStatus.INVALID)


def get_token_expiry_seconds() -> int:
    """Return the token expiry time in seconds."""
    return TOKEN_EXPIRY_SECONDS


def generate_verification_token(user_id: str, email: str) -> str:
    """
    Generate a JWT token for email verification.

    Args:
        user_id: The user's UUID
        email: The user's email address

    Returns:
        Encoded JWT verification token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "email_verification",
        "iat": now,
        "exp": now + timedelta(seconds=settings.VERIFICATION_TOKEN_EXPIRY_SECONDS),
    }
    return jwt.encode(payload, settings.JWT_KEY, algorithm='HS256')


def verify_verification_token(token: str) -> Optional[dict]:
    """
    Verify and decode an email verification token.

    Args:
        token: The verification JWT token

    Returns:
        Decoded token payload if valid and purpose matches, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.JWT_KEY, algorithms=['HS256'])
        if payload.get("purpose") != "email_verification":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_password_reset_token(user_id: str, email: str) -> str:
    """Generate a JWT token for password reset."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "password_reset",
        "iat": now,
        "exp": now + timedelta(seconds=settings.PASSWORD_RESET_TOKEN_EXPIRY_SECONDS),
    }
    return jwt.encode(payload, settings.JWT_KEY, algorithm='HS256')


def verify_password_reset_token(token: str) -> Optional[dict]:
    """Verify and decode a password reset token."""
    try:
        payload = jwt.decode(token, settings.JWT_KEY, algorithms=['HS256'])
        if payload.get("purpose") != "password_reset":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
