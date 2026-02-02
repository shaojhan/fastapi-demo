from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from .unitofwork.UserUnitOfWork import UserUnitOfWork
from ..exceptions.UserException import (
    UserHasAlreadyExistedError, UserNotFoundError, PasswordError, AuthenticationError,
    VerificationTokenExpiredError, EmailAlreadyVerifiedError, PasswordResetTokenExpiredError
)

from passlib.context import CryptContext
from uuid import uuid4

from app.repositories.sqlalchemy.UserRepository import UserQueryRepository
from app.utils.token_generator import (
    generate_verification_token, verify_verification_token,
    generate_password_reset_token, verify_password_reset_token
)
from app.services.EmailService import EmailService

if TYPE_CHECKING:
    from ..router.schemas.UserSchema import UserSchema


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Application service for user management operations."""

    def generate_uuid(self):
        return uuid4()

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    def _split_user_profile(self, user_model: UserSchema):
        """Split user schema into registration and profile data."""
        from ..router.schemas.UserSchema import UserRegistrationInput, UserProfileInput

        registration_keys = set(UserRegistrationInput.model_fields.keys())
        profile_keys = set(UserProfileInput.model_fields.keys())

        user_data = user_model.model_dump()

        user_registration_dict = {k: v for k, v in user_data.items() if k in registration_keys}
        user_registration_dict['id'] = self.generate_uuid()
        # Hash the password before storing
        user_registration_dict['pwd'] = self._hash_password(user_registration_dict['pwd'])

        profile_dict = {k: v for k, v in user_data.items() if k in profile_keys}

        user_registration_model = UserRegistrationInput(**user_registration_dict)
        profile_model = UserProfileInput(**profile_dict)

        return user_registration_model, profile_model

    def add_user_profile(self, user_model: UserSchema):
        """
        Create a new user with profile and send verification email.

        Args:
            user_model: User data from request

        Returns:
            The created user entity

        Raises:
            UserHasAlreadyExistedError: If user already exists
        """
        user_registration_model, profile_model = self._split_user_profile(user_model)

        with UserUnitOfWork() as uow:
            # Check if user already exists
            if uow.repo.exists_by_uid(user_registration_model.uid):
                raise UserHasAlreadyExistedError()

            user = uow.repo.add(user_registration_model.model_dump(), profile_model.model_dump())
            uow.commit()

            # Generate verification token and send email
            token = generate_verification_token(
                user_id=str(user.id),
                email=user.email
            )
            self._pending_verification = (user.email, token)

            return user

    async def send_pending_verification_email(self) -> None:
        """Send the verification email for the most recently created user."""
        if hasattr(self, '_pending_verification'):
            email, token = self._pending_verification
            email_service = EmailService()
            await email_service.send_verification_email(email, token)
            del self._pending_verification

    def verify_email(self, token: str) -> None:
        """
        Verify a user's email using the verification token.

        Args:
            token: JWT verification token

        Raises:
            VerificationTokenExpiredError: If token is invalid or expired
            EmailAlreadyVerifiedError: If email is already verified
        """
        payload = verify_verification_token(token)
        if not payload:
            raise VerificationTokenExpiredError()

        user_id = payload.get("sub")
        if not user_id:
            raise VerificationTokenExpiredError()

        with UserUnitOfWork() as uow:
            user = uow.repo.get_by_id(user_id)
            if not user:
                raise VerificationTokenExpiredError()

            if user.email_verified:
                raise EmailAlreadyVerifiedError()

            uow.repo.verify_email(user_id)
            uow.commit()

    def resend_verification_email(self, email: str) -> str:
        """
        Resend verification email for a user.

        Args:
            email: The user's email address

        Returns:
            The verification token (for async email sending)

        Raises:
            UserNotFoundError: If no user with that email
            EmailAlreadyVerifiedError: If already verified
        """
        with UserUnitOfWork() as uow:
            user = uow.repo.get_by_email(email)
            if not user:
                raise UserNotFoundError()

            if user.email_verified:
                raise EmailAlreadyVerifiedError()

            token = generate_verification_token(
                user_id=user.id,
                email=user.email
            )
            return token


    def update_user_profile(self, user_id: str, name: str, birthdate: date, description: str):
        """
        Update an existing user's profile.

        Args:
            user_id: The user's UUID string
            name: Updated name
            birthdate: Updated birthdate
            description: Updated description

        Returns:
            Updated UserModel

        Raises:
            UserNotFoundError: If user does not exist
        """
        with UserUnitOfWork() as uow:
            updated_user = uow.repo.update_profile(
                user_id=user_id,
                name=name,
                birthdate=birthdate,
                description=description
            )
            if not updated_user:
                raise UserNotFoundError()
            uow.commit()
            return updated_user


    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash using bcrypt."""
        return pwd_context.verify(plain_password, hashed_password)

    def update_password(self, user_id: str, old_password: str, new_password: str):
        """
        Update a user's password after verifying the old password.

        Args:
            user_id: The user's UUID string
            old_password: The current plain text password
            new_password: The new plain text password

        Raises:
            UserNotFoundError: If user does not exist
            AuthenticationError: If old password is incorrect
        """
        with UserUnitOfWork() as uow:
            user = uow.repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError()

            try:
                user.change_password(
                    old_password=old_password,
                    new_password=new_password,
                    verify_func=self._verify_password,
                    hash_func=self._hash_password
                )
            except ValueError:
                raise AuthenticationError(message="Old password is incorrect")

            uow.repo.update_password(
                user_id=user_id,
                new_hashed_password=user._hashed_password.value
            )
            uow.commit()

    def forgot_password(self, email: str) -> str:
        """
        Generate a password reset token for a user.

        Args:
            email: The user's email address

        Returns:
            The password reset token (for async email sending)

        Raises:
            UserNotFoundError: If no user with that email
        """
        with UserUnitOfWork() as uow:
            user = uow.repo.get_by_email(email)
            if not user:
                raise UserNotFoundError()

            return generate_password_reset_token(
                user_id=user.id,
                email=user.email
            )

    def reset_password(self, token: str, new_password: str) -> None:
        """
        Reset a user's password using a password reset token.

        Args:
            token: JWT password reset token
            new_password: The new plain text password

        Raises:
            PasswordResetTokenExpiredError: If token is invalid or expired
            UserNotFoundError: If user not found
        """
        payload = verify_password_reset_token(token)
        if not payload:
            raise PasswordResetTokenExpiredError()

        user_id = payload.get("sub")
        if not user_id:
            raise PasswordResetTokenExpiredError()

        with UserUnitOfWork() as uow:
            user = uow.repo.get_by_id(user_id)
            if not user:
                raise PasswordResetTokenExpiredError()

            new_hashed = self._hash_password(new_password)
            uow.repo.update_password(user_id=user_id, new_hashed_password=new_hashed)
            uow.commit()


class UserQueryService:
    """Query service for read-only user operations."""

    def get_all_users(self, page: int, size: int):
        from app.services.unitofwork.UserUnitOfWork import UserQueryUnitOfWork
        with UserQueryUnitOfWork() as uow:
            return uow.query_repo.get_all(page, size)
