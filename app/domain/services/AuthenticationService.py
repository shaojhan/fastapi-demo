from dataclasses import dataclass

from app.utils.token_generator import (
    generate_token,
    verify_token,
    get_token_expiry_seconds,
    TokenVerificationResult,
)


@dataclass
class AuthToken:
    """
    Value Object representing an authentication token.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

    @staticmethod
    def create(access_token: str) -> "AuthToken":
        """Create an AuthToken with the configured expiry time."""
        return AuthToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expiry_seconds()
        )


class AuthenticationDomainService:
    """
    Domain Service for authentication-related operations.
    Handles token creation and verification.
    """

    def create_token(self, user_id: str, uid: str) -> AuthToken:
        """
        Create a JWT token for the authenticated user.

        Args:
            user_id: The user's UUID
            uid: The user's username

        Returns:
            An AuthToken containing the JWT and metadata
        """
        access_token = generate_token(user_id, uid)
        return AuthToken.create(access_token)

    def verify_token(self, token: str) -> TokenVerificationResult:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token to verify

        Returns:
            TokenVerificationResult with status and payload
        """
        return verify_token(token)
