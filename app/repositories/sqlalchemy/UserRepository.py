from typing import Optional, List
from datetime import date
from uuid import UUID

from sqlalchemy import or_

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
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
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

    def exists_by_email(self, email: str) -> bool:
        """
        Check if a user with the given email exists.

        Args:
            email: The email to check

        Returns:
            True if exists, False otherwise
        """
        return self.db.query(User).filter(User.email == email).first() is not None

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
            description=user.profile.description if user.profile else None,
            avatar=user.profile.avatar if user.profile else None
        )

        return UserModel.reconstitute(
            id=str(user.id),
            uid=user.uid,
            email=user.email,
            hashed_password=user.pwd,
            profile=profile,
            role=user.role,
            email_verified=user.email_verified,
            google_id=user.google_id
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
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
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
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return False

        user.pwd = new_hashed_password
        self.db.flush()
        return True

    def update_role(self, user_id: str, new_role: UserRole) -> bool:
        """
        Update a user's role.

        Args:
            user_id: The user's UUID
            new_role: The new UserRole enum value

        Returns:
            True if updated, False if user not found
        """
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return False

        user.role = new_role
        self.db.flush()
        return True

    def get_by_google_id(self, google_id: str) -> Optional[UserModel]:
        """Get a user by their Google OAuth ID."""
        user = self.db.query(User).filter(User.google_id == google_id).first()
        if not user:
            return None
        return self._to_domain_model(user)

    def link_google_id(self, user_id: str, google_id: str) -> bool:
        """Link a Google account to an existing user."""
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return False
        user.google_id = google_id
        self.db.flush()
        return True

    def verify_email(self, user_id: str) -> bool:
        """
        Mark a user's email as verified.

        Args:
            user_id: The user's UUID

        Returns:
            True if updated, False if user not found
        """
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return False
        user.email_verified = True
        self.db.flush()
        return True

    def update_avatar(self, user_id: str, avatar_url: str) -> Optional[str]:
        """
        Update a user's avatar.

        Args:
            user_id: The user's UUID
            avatar_url: The avatar file URL/path

        Returns:
            The avatar URL if updated, None if user not found
        """
        user = self.db.query(User).filter(User.id == UUID(user_id)).first()
        if not user or not user.profile:
            return None
        user.profile.avatar = avatar_url
        self.db.flush()
        return avatar_url

    def delete(self):
        pass


class UserQueryRepository(BaseRepository):
    """Query repository for read-only user operations."""

    def get_all(self, page: int, size: int) -> tuple[list[UserModel], int]:
        """
        Get paginated list of all users.

        Returns:
            Tuple of (list of UserModel, total count)
        """
        query = self.db.query(User)
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return [self._to_domain_model(u) for u in users], total

    def search_users(
        self,
        keyword: str,
        exclude_user_id: str | None = None,
        limit: int = 20
    ) -> tuple[List[UserModel], int]:
        """
        Search users by uid, email, or name.

        Args:
            keyword: Search keyword
            exclude_user_id: User ID to exclude from results (usually current user)
            limit: Maximum number of results

        Returns:
            Tuple of (list of UserModel, total count)
        """
        query = self.db.query(User).outerjoin(Profile)

        # Search in uid, email, and profile name
        search_filter = or_(
            User.uid.ilike(f"%{keyword}%"),
            User.email.ilike(f"%{keyword}%"),
            Profile.name.ilike(f"%{keyword}%")
        )
        query = query.filter(search_filter)

        # Exclude current user
        if exclude_user_id:
            query = query.filter(User.id != UUID(exclude_user_id))

        total = query.count()
        users = query.order_by(User.uid).limit(limit).all()

        return [self._to_domain_model(u) for u in users], total

    def _to_domain_model(self, user: User) -> UserModel:
        profile = DomainProfile(
            name=user.profile.name if user.profile else None,
            birthdate=user.profile.birthdate if user.profile else None,
            description=user.profile.description if user.profile else None,
            avatar=user.profile.avatar if user.profile else None
        )
        return UserModel.reconstitute(
            id=str(user.id),
            uid=user.uid,
            email=user.email,
            hashed_password=user.pwd,
            profile=profile,
            role=user.role,
            email_verified=user.email_verified,
            google_id=user.google_id
        )
