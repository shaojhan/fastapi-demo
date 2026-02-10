from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class SSOProtocol(str, Enum):
    SAML = "SAML"
    OIDC = "OIDC"


@dataclass(frozen=True)
class SAMLConfig:
    """Value Object for SAML IdP configuration."""
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str
    idp_slo_url: str | None = None


@dataclass(frozen=True)
class OIDCConfig:
    """Value Object for OIDC configuration."""
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str | None = None
    jwks_uri: str | None = None
    scopes: str = "openid email profile"


@dataclass(frozen=True)
class AttributeMapping:
    """Value Object for IdP claim → internal field mapping."""
    email: str = "email"
    name: str = "name"
    external_id: str = "sub"

    @staticmethod
    def from_dict(data: dict | None) -> "AttributeMapping":
        if not data:
            return AttributeMapping()
        return AttributeMapping(
            email=data.get("email", "email"),
            name=data.get("name", "name"),
            external_id=data.get("external_id", "sub"),
        )

    def to_dict(self) -> dict:
        return {
            "email": self.email,
            "name": self.name,
            "external_id": self.external_id,
        }


class SSOProviderModel:
    """
    Aggregate Root representing an SSO Provider.
    Use factory methods `create` or `reconstitute` to create instances.
    """

    def __init__(
        self,
        id: str,
        name: str,
        slug: str,
        protocol: SSOProtocol,
        saml_config: SAMLConfig | None = None,
        oidc_config: OIDCConfig | None = None,
        attribute_mapping: AttributeMapping | None = None,
        is_active: bool = False,
        display_order: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self._id = id
        self._name = name
        self._slug = slug
        self._protocol = protocol
        self._saml_config = saml_config
        self._oidc_config = oidc_config
        self._attribute_mapping = attribute_mapping or AttributeMapping()
        self._is_active = is_active
        self._display_order = display_order
        self._created_at = created_at
        self._updated_at = updated_at

    # Properties
    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def slug(self) -> str:
        return self._slug

    @property
    def protocol(self) -> SSOProtocol:
        return self._protocol

    @property
    def saml_config(self) -> SAMLConfig | None:
        return self._saml_config

    @property
    def oidc_config(self) -> OIDCConfig | None:
        return self._oidc_config

    @property
    def attribute_mapping(self) -> AttributeMapping:
        return self._attribute_mapping

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def display_order(self) -> int:
        return self._display_order

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    # Factory methods
    @staticmethod
    def create(
        name: str,
        slug: str,
        protocol: SSOProtocol,
        saml_config: SAMLConfig | None = None,
        oidc_config: OIDCConfig | None = None,
        attribute_mapping: AttributeMapping | None = None,
        display_order: int = 0,
    ) -> "SSOProviderModel":
        if not name or not name.strip():
            raise ValueError("Provider name cannot be empty")
        if not slug or not slug.strip():
            raise ValueError("Provider slug cannot be empty")

        if protocol == SSOProtocol.SAML and not saml_config:
            raise ValueError("SAML configuration is required for SAML protocol")
        if protocol == SSOProtocol.OIDC and not oidc_config:
            raise ValueError("OIDC configuration is required for OIDC protocol")

        return SSOProviderModel(
            id=str(uuid4()),
            name=name.strip(),
            slug=slug.strip().lower(),
            protocol=protocol,
            saml_config=saml_config,
            oidc_config=oidc_config,
            attribute_mapping=attribute_mapping or AttributeMapping(),
            is_active=False,
            display_order=display_order,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def reconstitute(
        id: str,
        name: str,
        slug: str,
        protocol: SSOProtocol,
        saml_config: SAMLConfig | None = None,
        oidc_config: OIDCConfig | None = None,
        attribute_mapping: AttributeMapping | None = None,
        is_active: bool = False,
        display_order: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "SSOProviderModel":
        return SSOProviderModel(
            id=id,
            name=name,
            slug=slug,
            protocol=protocol,
            saml_config=saml_config,
            oidc_config=oidc_config,
            attribute_mapping=attribute_mapping,
            is_active=is_active,
            display_order=display_order,
            created_at=created_at,
            updated_at=updated_at,
        )

    # Business methods
    def update(
        self,
        name: str | None = None,
        saml_config: SAMLConfig | None = None,
        oidc_config: OIDCConfig | None = None,
        attribute_mapping: AttributeMapping | None = None,
        display_order: int | None = None,
    ) -> None:
        if name is not None:
            if not name.strip():
                raise ValueError("Provider name cannot be empty")
            self._name = name.strip()

        if self._protocol == SSOProtocol.SAML and saml_config is not None:
            self._saml_config = saml_config
        if self._protocol == SSOProtocol.OIDC and oidc_config is not None:
            self._oidc_config = oidc_config

        if attribute_mapping is not None:
            self._attribute_mapping = attribute_mapping
        if display_order is not None:
            self._display_order = display_order

        self._updated_at = datetime.utcnow()

    def activate(self) -> None:
        if self._is_active:
            raise ValueError("Provider is already active")
        self._validate_config()
        self._is_active = True
        self._updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        if not self._is_active:
            raise ValueError("Provider is already inactive")
        self._is_active = False
        self._updated_at = datetime.utcnow()

    def _validate_config(self) -> None:
        if self._protocol == SSOProtocol.SAML:
            if not self._saml_config:
                raise ValueError("SAML configuration is required")
        elif self._protocol == SSOProtocol.OIDC:
            if not self._oidc_config:
                raise ValueError("OIDC configuration is required")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SSOProviderModel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class SSOGlobalConfig:
    """
    Value Object representing the global SSO configuration (singleton).
    """

    def __init__(
        self,
        auto_create_users: bool = False,
        enforce_sso: bool = False,
        default_role: str = "NORMAL",
    ):
        self._auto_create_users = auto_create_users
        self._enforce_sso = enforce_sso
        self._default_role = default_role

    @property
    def auto_create_users(self) -> bool:
        return self._auto_create_users

    @property
    def enforce_sso(self) -> bool:
        return self._enforce_sso

    @property
    def default_role(self) -> str:
        return self._default_role

    def update(
        self,
        auto_create_users: bool | None = None,
        enforce_sso: bool | None = None,
        default_role: str | None = None,
    ) -> None:
        if auto_create_users is not None:
            self._auto_create_users = auto_create_users
        if enforce_sso is not None:
            self._enforce_sso = enforce_sso
        if default_role is not None:
            valid_roles = ["NORMAL", "EMPLOYEE"]
            if default_role not in valid_roles:
                raise ValueError(f"Default role must be one of: {valid_roles}")
            self._default_role = default_role


@dataclass(frozen=True)
class SSOUserLink:
    """Value Object representing an SSO user link."""
    id: str
    user_id: str
    provider_id: str
    external_id: str
    created_at: datetime | None = None
