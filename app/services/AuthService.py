from typing import Optional

from passlib.context import CryptContext

from app.domain.UserModel import UserModel
from app.domain.services.AuthenticationService import AuthToken, AuthenticationDomainService
from app.services.unitofwork.UserUnitOfWork import UserUnitOfWork
from app.exceptions.UserException import (
    AuthenticationError,
    UserNotFoundError,
    EmailNotVerifiedError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.utils.token_generator import TokenVerificationResult


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Application Service for authentication operations.
    Coordinates between domain services, repositories, and infrastructure.
    """

    def __init__(self):
        self._auth_domain_service = AuthenticationDomainService()

    def login(self, username: str, password: str) -> tuple[AuthToken, UserModel]:
        """
        Authenticate a user and return a JWT token.

        Args:
            username: The user's uid or email
            password: The user's plain text password

        Returns:
            A tuple of (AuthToken, UserModel)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        with UserUnitOfWork() as uow:
            # Try to find user by uid first, then by email
            user = uow.repo.get_by_uid(username)
            if not user:
                user = uow.repo.get_by_email(username)

            if not user:
                raise AuthenticationError(message="Invalid username or password")

            # Verify password using domain model
            if not user.verify_password(password, self._verify_password):
                raise AuthenticationError(message="Invalid username or password")

            # Check email verification
            if not user.email_verified:
                raise EmailNotVerifiedError()

            # Create token using domain service
            token = self._auth_domain_service.create_token(
                user_id=user.id,
                uid=user.uid
            )

            return token, user

    def verify_token(self, token: str) -> TokenVerificationResult:
        """
        Verify a JWT token and return the verification result.

        Args:
            token: The JWT token to verify

        Returns:
            TokenVerificationResult with status and payload
        """
        return self._auth_domain_service.verify_token(token)

    def get_current_user(self, token: str) -> UserModel:
        """
        Get the current user from a JWT token.

        Args:
            token: The JWT token

        Returns:
            UserModel if token is valid

        Raises:
            TokenExpiredError: If the token has expired
            InvalidTokenError: If the token is invalid
        """
        result = self.verify_token(token)

        if result.is_expired:
            raise TokenExpiredError()

        if not result.is_valid:
            raise InvalidTokenError()

        user_id = result.payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        with UserUnitOfWork() as uow:
            user = uow.repo.get_by_id(user_id)
            if not user:
                raise InvalidTokenError()
            return user

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash using bcrypt."""
        return pwd_context.verify(plain_password, hashed_password)
