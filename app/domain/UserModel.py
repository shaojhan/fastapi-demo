from dataclasses import dataclass
from enum import Enum
from datetime import date
import uuid
from typing import Callable


class UserRole(str, Enum):
    ADMIN = 'ADMIN'
    EMPLOYEE = 'EMPLOYEE'
    NORMAL = 'NORMAL'


class AccountType(str, Enum):
    REAL = 'REAL'
    TEST = 'TEST'
    SYSTEM = 'SYSTEM'


@dataclass(frozen=True)
class Profile:
    """
    A Value Object representing a user's profile information.
    """
    name: str | None = None
    birthdate: date | None = None
    description: str | None = None
    avatar: str | None = None


@dataclass
class HashedPassword:
    """
    A Value Object representing a hashed password.
    """
    value: str

    def verify(
        self,
        raw_password: str,
        verify_func: Callable[[str, str], bool]
    ) -> bool:
        """
        Verify the raw password against the hashed value.

        Args:
            raw_password: The plain text password to verify
            verify_func: A function that takes (raw_password, hashed_password)
                         and returns True if they match

        Returns:
            True if the password matches, False otherwise
        """
        return verify_func(raw_password, self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HashedPassword):
            return NotImplemented
        return self.value == other.value


class UserModel:
    """
    An Aggregate Root representing a user in the domain.
    The constructor should be treated as internal.
    Use factory methods like `register` or `reconstitute` to create instances.
    """
    def __init__(
        self,
        id: str,
        uid: str,
        email: str,
        hashed_password: HashedPassword,
        profile: Profile,
        role: UserRole = UserRole.NORMAL,
        account_type: AccountType = AccountType.REAL,
        email_verified: bool = False,
        google_id: str | None = None
    ):
        self._id = id
        self._uid = uid
        self._email = email
        self._hashed_password = hashed_password
        self._profile = profile
        self._role = role
        self._account_type = account_type
        self._email_verified = email_verified
        self._google_id = google_id

    @property
    def id(self) -> str:
        return self._id

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def email(self) -> str:
        return self._email

    @property
    def profile(self) -> Profile:
        return self._profile

    @property
    def role(self) -> UserRole:
        return self._role

    @property
    def account_type(self) -> AccountType:
        return self._account_type

    @property
    def email_verified(self) -> bool:
        return self._email_verified

    @property
    def google_id(self) -> str | None:
        return self._google_id

    def link_google(self, google_id: str) -> None:
        """Link a Google account to this user."""
        self._google_id = google_id

    def verify_email(self) -> None:
        """Mark this user's email as verified."""
        self._email_verified = True

    @staticmethod
    def register(
        uid: str,
        raw_password: str,
        email: str,
        hash_func: Callable[[str], str]
    ) -> "UserModel":
        """
        Factory method to create a new user with a hashed password.

        Args:
            uid: Username
            raw_password: Plain text password
            email: User's email
            hash_func: Function to hash the password

        Returns:
            A new UserModel instance
        """
        hashed_password = HashedPassword(hash_func(raw_password))

        return UserModel(
            id=str(uuid.uuid4()),
            uid=uid,
            email=email,
            hashed_password=hashed_password,
            profile=Profile(),
            role=UserRole.NORMAL,
            account_type=AccountType.REAL,
        )

    @staticmethod
    def reconstitute(
        id: str,
        uid: str,
        email: str,
        hashed_password: str,
        profile: Profile,
        role: UserRole,
        account_type: AccountType = AccountType.REAL,
        email_verified: bool = False,
        google_id: str | None = None
    ) -> "UserModel":
        """
        Factory method to reconstitute a user from persistence.

        Args:
            id: User's UUID
            uid: Username
            email: User's email
            hashed_password: Already hashed password from database
            profile: User's profile
            role: User's role
            account_type: Account type (REAL, TEST, SYSTEM)
            email_verified: Whether the user's email has been verified
            google_id: Google OAuth ID if linked

        Returns:
            A reconstituted UserModel instance
        """
        return UserModel(
            id=id,
            uid=uid,
            email=email,
            hashed_password=HashedPassword(hashed_password),
            profile=profile,
            role=role,
            account_type=account_type,
            email_verified=email_verified,
            google_id=google_id
        )

    def verify_password(
        self,
        raw_password: str,
        verify_func: Callable[[str, str], bool]
    ) -> bool:
        """
        Verify if the provided password matches the user's password.

        Args:
            raw_password: The plain text password to verify
            verify_func: A function that takes (raw_password, hashed_password)
                         and returns True if they match

        Returns:
            True if the password matches, False otherwise
        """
        return self._hashed_password.verify(raw_password, verify_func)

    def change_password(
        self,
        old_password: str,
        new_password: str,
        verify_func: Callable[[str, str], bool],
        hash_func: Callable[[str], str]
    ) -> None:
        """
        Change the user's password after verifying the old password.

        Args:
            old_password: The current plain text password
            new_password: The new plain text password
            verify_func: Function to verify (raw_password, hashed_password) -> bool
            hash_func: Function to hash a plain text password

        Raises:
            ValueError: If old password verification fails
        """
        if not self._hashed_password.verify(old_password, verify_func):
            raise ValueError("Old password is incorrect")
        self._hashed_password = HashedPassword(hash_func(new_password))

    def promote_to_employee(self) -> None:
        """
        Promote this user's role to EMPLOYEE.

        Raises:
            ValueError: If user is already an EMPLOYEE
            ValueError: If user is an ADMIN (cannot change admin role)
        """
        if self._role == UserRole.EMPLOYEE:
            raise ValueError("User is already an employee")
        if self._role == UserRole.ADMIN:
            raise ValueError("Cannot change role of an admin user")
        self._role = UserRole.EMPLOYEE

    def update_profile(self, name: str, birthdate: date, description: str):
        """Update the user's profile information."""
        self._profile = Profile(name=name, birthdate=birthdate, description=description)
