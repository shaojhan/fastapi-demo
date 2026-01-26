from typing import Optional
from datetime import date

from .BaseRepository import BaseRepository
from database.models.user import User, Profile
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile


class UserRepository(BaseRepository):
    """Repository for User aggregate persistence operations."""

    def add(self, user_dict: dict, profile_dict: dict) -> User:
        """
        Add a new user with profile to the database.

        Args:
            user_dict: Dictionary containing user data
            profile_dict: Dictionary containing profile data

        Returns:
            The created User entity
        """
        user = User(**user_dict)
        profile = Profile(**profile_dict)
        user.profile = profile

        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def get_by_uid(self, uid: str) -> Optional[UserModel]:
        """
        Get a user by their username (uid).

        Args:
            uid: The user's username

        Returns:
            UserModel if found, None otherwise
        """
        user = self.db.query(User).filter(User.uid == uid).first()
        if not user:
            return None
        return self._to_domain_model(user)

    def get_by_id(self, user_id: str) -> Optional[UserModel]:
        """
        Get a user by their UUID.

        Args:
            user_id: The user's UUID

        Returns:
            UserModel if found, None otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        return self._to_domain_model(user)

    def get_by_email(self, email: str) -> Optional[UserModel]:
        """
        Get a user by their email.

        Args:
            email: The user's email

        Returns:
            UserModel if found, None otherwise
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        return self._to_domain_model(user)

    def exists_by_uid(self, uid: str) -> bool:
        """
        Check if a user with the given uid exists.

        Args:
            uid: The username to check

        Returns:
            True if exists, False otherwise
        """
        return self.db.query(User).filter(User.uid == uid).first() is not None

    def _to_domain_model(self, user: User) -> UserModel:
        """
        Convert a User ORM entity to a UserModel domain object.

        Args:
            user: The User ORM entity

        Returns:
            A UserModel domain object
        """
        profile = DomainProfile(
            name=user.profile.name if user.profile else None,
            birthdate=user.profile.birthdate if user.profile else None,
            description=user.profile.description if user.profile else None
        )

        return UserModel.reconstitute(
            id=str(user.id),
            uid=user.uid,
            email=user.email,
            hashed_password=user.pwd,
            profile=profile,
            role=user.role
        )

    def update_profile(self, user_id: str, name: str, birthdate: date, description: str) -> Optional[UserModel]:
        """
        Update a user's profile.

        Args:
            user_id: The user's UUID
            name: Updated name
            birthdate: Updated birthdate
            description: Updated description

        Returns:
            Updated UserModel if found, None otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            return None

        user.profile.name = name
        user.profile.birthdate = birthdate
        user.profile.description = description

        self.db.flush()
        self.db.refresh(user)
        return self._to_domain_model(user)

    def update_password(self, user_id: str, new_hashed_password: str) -> bool:
        """
        Update a user's password.

        Args:
            user_id: The user's UUID
            new_hashed_password: The new hashed password

        Returns:
            True if updated, False if user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.pwd = new_hashed_password
        self.db.flush()
        return True

    def delete(self):
        pass


class UserQueryRepository(BaseRepository):
    """Query repository for read-only user operations."""
    pass
