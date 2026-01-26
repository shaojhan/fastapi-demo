from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from .unitofwork.UserUnitOfWork import UserUnitOfWork
from ..exceptions.UserException import UserHasAlreadyExistedError, UserNotFoundError, PasswordError, AuthenticationError

from passlib.context import CryptContext
from uuid import uuid4

from app.repositories.sqlalchemy.UserRepository import UserQueryRepository

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
        Create a new user with profile.

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
            return user


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


class UserQueryService:
    """Query service for read-only user operations."""

    def __init__(self):
        self.userquery_repo = UserQueryRepository()
