from dataclasses import dataclass


@dataclass
class AuthorityModel:
    """
    An Entity representing an authority/permission in the domain.
    Authorities define specific permissions that can be assigned to roles.
    """
    id: int | None
    name: str
    description: str | None = None

    @staticmethod
    def create(name: str, description: str | None = None) -> "AuthorityModel":
        """
        Factory method to create a new authority.

        Args:
            name: The unique name of the authority (e.g., "USER_READ", "USER_WRITE")
            description: Optional description of what this authority allows

        Returns:
            A new AuthorityModel instance
        """
        if not name or not name.strip():
            raise ValueError("Authority name cannot be empty")

        return AuthorityModel(
            id=None,  # ID will be assigned by the database
            name=name.strip().upper(),
            description=description
        )

    def update_description(self, description: str | None):
        """
        Update the authority's description.

        Args:
            description: New description for the authority
        """
        self.description = description

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AuthorityModel):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)
