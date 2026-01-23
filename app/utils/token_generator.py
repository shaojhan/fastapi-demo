import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.config import get_settings

settings = get_settings()

# Token expiration time in seconds (1 hour)
TOKEN_EXPIRY_SECONDS = 3600


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


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        decoded_token = jwt.decode(
            token,
            settings.JWT_KEY,
            algorithms=['HS256']
        )
        return decoded_token
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_expiry_seconds() -> int:
    """Return the token expiry time in seconds."""
    return TOKEN_EXPIRY_SECONDS
