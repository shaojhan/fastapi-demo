from dataclasses import dataclass
from enum import Enum
from datetime import date
import uuid
from typing import Callable

class UserRole(str, Enum):
    ADMIN = 'ADMIN'
    EMPLOYEE = 'EMPLOYEE'
    NORMAL = 'NORMAL'

@dataclass(frozen=True)
class Profile:
    """
    A Value Object representing a user's profile information.
    """
    name: str | None = None
    birthdate: date | None = None
    description: str | None = None

@dataclass
class HashedPassword:
    password: str

    def __eq__(self, other: object) -> bool:
        # In a real application, this should be a constant-time comparison
        # to prevent timing attacks.
        if not isinstance(other, HashedPassword):
            return NotImplemented
        return self.password == other.password

class UserModel:
    """
    An Aggregate Root representing a user in the domain.
    The constructor should be treated as internal.
    Use factory methods like `register` to create new instances.
    """
    def __init__(
        self,
        id: str,
        uid: str,
        email: str,
        hashed_password: HashedPassword,
        profile: Profile,
        role: UserRole = UserRole.NORMAL
    ): 
        self.id = id
        self.uid = uid
        self.email = email
        self._hashed_password = hashed_password
        self.profile = profile
        self.role = role

    @staticmethod
    def register(uid: str, raw_password: str, email: str) -> "UserModel":
        # In a real app, the password hashing function would be injected
        # or called from a dedicated service.
        # For this example, we'll pretend a simple "hash" operation.
        hashed_password = HashedPassword(f"hashed_{raw_password}")

        return UserModel(
            id=str(uuid.uuid4()),
            uid=uid,
            email=email,
            hashed_password=hashed_password,
            profile=Profile(), # Start with an empty profile
            role=UserRole.NORMAL
        )

    def verify_password(self, raw_password: str) -> bool:
        # Again, this is a simplified representation of hashing for comparison.
        return self._hashed_password == HashedPassword(f"hashed_{raw_password}")

    def update_profile(self, name: str, birthdate: date, description: str):
        self.profile = Profile(name=name, birthdate=birthdate, description=description)