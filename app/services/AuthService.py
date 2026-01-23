from typing import Optional

from passlib.context import CryptContext

from app.domain.UserModel import UserModel
from app.domain.services.AuthenticationService import AuthToken, AuthenticationDomainService
from app.services.unitofwork.UserUnitOfWork import UserUnitOfWork
from app.exceptions.UserException import AuthenticationError, UserNotFoundError


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Application Service for authentication operations.
    Coordinates between domain services, repositories, and infrastructure.
    """

    def __init__(self):
        self._auth_domain_service = AuthenticationDomainService()

    def login(self, uid: str, password: str) -> tuple[AuthToken, UserModel]:
        """
        Authenticate a user and return a JWT token.

        Args:
            uid: The user's username
            password: The user's plain text password

        Returns:
            A tuple of (AuthToken, UserModel)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        with UserUnitOfWork() as uow:
            # Get user from repository
            user = uow.repo.get_by_uid(uid)

            if not user:
                raise AuthenticationError(message="Invalid username or password")

            # Verify password using domain model
            if not user.verify_password(password, self._verify_password):
                raise AuthenticationError(message="Invalid username or password")

            # Create token using domain service
            token = self._auth_domain_service.create_token(
                user_id=user.id,
                uid=user.uid
            )

            return token, user

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify a JWT token and return the payload.

        Args:
            token: The JWT token to verify

        Returns:
            Token payload if valid, None otherwise
        """
        return self._auth_domain_service.verify_token(token)

    def get_current_user(self, token: str) -> Optional[UserModel]:
        """
        Get the current user from a JWT token.

        Args:
            token: The JWT token

        Returns:
            UserModel if token is valid, None otherwise
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        with UserUnitOfWork() as uow:
            return uow.repo.get_by_id(user_id)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash using bcrypt."""
        return pwd_context.verify(plain_password, hashed_password)
