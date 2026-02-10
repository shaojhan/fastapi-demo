"""
Unit tests for SSO domain models.
"""
import pytest
from datetime import datetime
from uuid import UUID

from app.domain.SSOModel import (
    SSOProtocol,
    SAMLConfig,
    OIDCConfig,
    AttributeMapping,
    SSOProviderModel,
    SSOGlobalConfig,
    SSOUserLink,
)


# --- Test Data ---
TEST_PROVIDER_NAME = "Okta"
TEST_PROVIDER_SLUG = "okta"

SAML_CONFIG_DATA = {
    "idp_entity_id": "https://okta.example.com/saml",
    "idp_sso_url": "https://okta.example.com/sso",
    "idp_x509_cert": "MIICpDCCAYwCCQD...",
    "sp_entity_id": "https://myapp.example.com/saml",
    "sp_acs_url": "https://myapp.example.com/api/sso/saml/okta/acs",
}

OIDC_CONFIG_DATA = {
    "client_id": "my-client-id",
    "client_secret": "my-client-secret",
    "authorization_url": "https://okta.example.com/authorize",
    "token_url": "https://okta.example.com/token",
}


class TestSSOProtocol:
    """測試 SSOProtocol 列舉"""

    def test_saml_value(self):
        assert SSOProtocol.SAML.value == "SAML"

    def test_oidc_value(self):
        assert SSOProtocol.OIDC.value == "OIDC"

    def test_from_string(self):
        assert SSOProtocol("SAML") == SSOProtocol.SAML
        assert SSOProtocol("OIDC") == SSOProtocol.OIDC


class TestSAMLConfig:
    """測試 SAMLConfig 值物件"""

    def test_creation(self):
        config = SAMLConfig(**SAML_CONFIG_DATA)
        assert config.idp_entity_id == SAML_CONFIG_DATA["idp_entity_id"]
        assert config.idp_sso_url == SAML_CONFIG_DATA["idp_sso_url"]
        assert config.idp_x509_cert == SAML_CONFIG_DATA["idp_x509_cert"]
        assert config.sp_entity_id == SAML_CONFIG_DATA["sp_entity_id"]
        assert config.sp_acs_url == SAML_CONFIG_DATA["sp_acs_url"]
        assert config.idp_slo_url is None

    def test_with_slo_url(self):
        config = SAMLConfig(**SAML_CONFIG_DATA, idp_slo_url="https://okta.example.com/slo")
        assert config.idp_slo_url == "https://okta.example.com/slo"

    def test_is_frozen(self):
        config = SAMLConfig(**SAML_CONFIG_DATA)
        with pytest.raises(AttributeError):
            config.idp_entity_id = "changed"


class TestOIDCConfig:
    """測試 OIDCConfig 值物件"""

    def test_creation(self):
        config = OIDCConfig(**OIDC_CONFIG_DATA)
        assert config.client_id == "my-client-id"
        assert config.client_secret == "my-client-secret"
        assert config.authorization_url == "https://okta.example.com/authorize"
        assert config.token_url == "https://okta.example.com/token"
        assert config.userinfo_url is None
        assert config.jwks_uri is None
        assert config.scopes == "openid email profile"

    def test_with_optional_fields(self):
        config = OIDCConfig(
            **OIDC_CONFIG_DATA,
            userinfo_url="https://okta.example.com/userinfo",
            jwks_uri="https://okta.example.com/jwks",
            scopes="openid email",
        )
        assert config.userinfo_url == "https://okta.example.com/userinfo"
        assert config.jwks_uri == "https://okta.example.com/jwks"
        assert config.scopes == "openid email"

    def test_is_frozen(self):
        config = OIDCConfig(**OIDC_CONFIG_DATA)
        with pytest.raises(AttributeError):
            config.client_id = "changed"


class TestAttributeMapping:
    """測試 AttributeMapping 值物件"""

    def test_default_values(self):
        mapping = AttributeMapping()
        assert mapping.email == "email"
        assert mapping.name == "name"
        assert mapping.external_id == "sub"

    def test_from_dict(self):
        data = {"email": "mail", "name": "displayName", "external_id": "nameId"}
        mapping = AttributeMapping.from_dict(data)
        assert mapping.email == "mail"
        assert mapping.name == "displayName"
        assert mapping.external_id == "nameId"

    def test_from_dict_none(self):
        mapping = AttributeMapping.from_dict(None)
        assert mapping.email == "email"

    def test_from_dict_partial(self):
        mapping = AttributeMapping.from_dict({"email": "mail"})
        assert mapping.email == "mail"
        assert mapping.name == "name"
        assert mapping.external_id == "sub"

    def test_to_dict(self):
        mapping = AttributeMapping(email="mail", name="displayName", external_id="uid")
        result = mapping.to_dict()
        assert result == {"email": "mail", "name": "displayName", "external_id": "uid"}


class TestSSOProviderModel:
    """測試 SSOProviderModel 聚合根"""

    def test_create_saml_provider(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name=TEST_PROVIDER_NAME,
            slug=TEST_PROVIDER_SLUG,
            protocol=SSOProtocol.SAML,
            saml_config=saml,
        )

        assert provider.name == TEST_PROVIDER_NAME
        assert provider.slug == TEST_PROVIDER_SLUG
        assert provider.protocol == SSOProtocol.SAML
        assert provider.saml_config == saml
        assert provider.oidc_config is None
        assert provider.is_active is False
        assert provider.display_order == 0
        assert UUID(provider.id)  # valid UUID
        assert provider.created_at is not None

    def test_create_oidc_provider(self):
        oidc = OIDCConfig(**OIDC_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Azure AD",
            slug="azure-ad",
            protocol=SSOProtocol.OIDC,
            oidc_config=oidc,
        )

        assert provider.protocol == SSOProtocol.OIDC
        assert provider.oidc_config == oidc
        assert provider.saml_config is None

    def test_create_with_empty_name_raises(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        with pytest.raises(ValueError, match="Provider name cannot be empty"):
            SSOProviderModel.create(name="", slug="test", protocol=SSOProtocol.SAML, saml_config=saml)

    def test_create_with_empty_slug_raises(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        with pytest.raises(ValueError, match="Provider slug cannot be empty"):
            SSOProviderModel.create(name="Test", slug="", protocol=SSOProtocol.SAML, saml_config=saml)

    def test_create_saml_without_config_raises(self):
        with pytest.raises(ValueError, match="SAML configuration is required"):
            SSOProviderModel.create(name="Test", slug="test", protocol=SSOProtocol.SAML)

    def test_create_oidc_without_config_raises(self):
        with pytest.raises(ValueError, match="OIDC configuration is required"):
            SSOProviderModel.create(name="Test", slug="test", protocol=SSOProtocol.OIDC)

    def test_slug_is_lowercased(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Test", slug="My-Provider", protocol=SSOProtocol.SAML, saml_config=saml
        )
        assert provider.slug == "my-provider"

    def test_reconstitute(self):
        provider = SSOProviderModel.reconstitute(
            id="abc-123",
            name=TEST_PROVIDER_NAME,
            slug=TEST_PROVIDER_SLUG,
            protocol=SSOProtocol.SAML,
            saml_config=SAMLConfig(**SAML_CONFIG_DATA),
            is_active=True,
            display_order=1,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 6, 1),
        )

        assert provider.id == "abc-123"
        assert provider.is_active is True
        assert provider.display_order == 1
        assert provider.created_at == datetime(2024, 1, 1)
        assert provider.updated_at == datetime(2024, 6, 1)

    def test_update_name(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Old Name", slug="test", protocol=SSOProtocol.SAML, saml_config=saml
        )
        provider.update(name="New Name")
        assert provider.name == "New Name"
        assert provider.updated_at is not None

    def test_update_empty_name_raises(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Test", slug="test", protocol=SSOProtocol.SAML, saml_config=saml
        )
        with pytest.raises(ValueError, match="Provider name cannot be empty"):
            provider.update(name="  ")

    def test_update_saml_config(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Test", slug="test", protocol=SSOProtocol.SAML, saml_config=saml
        )
        new_saml = SAMLConfig(**{**SAML_CONFIG_DATA, "idp_sso_url": "https://new.example.com/sso"})
        provider.update(saml_config=new_saml)
        assert provider.saml_config.idp_sso_url == "https://new.example.com/sso"

    def test_update_display_order(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Test", slug="test", protocol=SSOProtocol.SAML, saml_config=saml
        )
        provider.update(display_order=5)
        assert provider.display_order == 5

    def test_activate(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Test", slug="test", protocol=SSOProtocol.SAML, saml_config=saml
        )
        provider.activate()
        assert provider.is_active is True

    def test_activate_already_active_raises(self):
        provider = SSOProviderModel.reconstitute(
            id="abc", name="Test", slug="test", protocol=SSOProtocol.SAML,
            saml_config=SAMLConfig(**SAML_CONFIG_DATA), is_active=True,
        )
        with pytest.raises(ValueError, match="already active"):
            provider.activate()

    def test_deactivate(self):
        provider = SSOProviderModel.reconstitute(
            id="abc", name="Test", slug="test", protocol=SSOProtocol.SAML,
            saml_config=SAMLConfig(**SAML_CONFIG_DATA), is_active=True,
        )
        provider.deactivate()
        assert provider.is_active is False

    def test_deactivate_already_inactive_raises(self):
        saml = SAMLConfig(**SAML_CONFIG_DATA)
        provider = SSOProviderModel.create(
            name="Test", slug="test", protocol=SSOProtocol.SAML, saml_config=saml
        )
        with pytest.raises(ValueError, match="already inactive"):
            provider.deactivate()

    def test_activate_without_config_raises(self):
        provider = SSOProviderModel.reconstitute(
            id="abc", name="Test", slug="test", protocol=SSOProtocol.SAML,
            saml_config=None, is_active=False,
        )
        with pytest.raises(ValueError, match="SAML configuration is required"):
            provider.activate()

    def test_equality(self):
        p1 = SSOProviderModel.reconstitute(
            id="abc", name="A", slug="a", protocol=SSOProtocol.SAML,
        )
        p2 = SSOProviderModel.reconstitute(
            id="abc", name="B", slug="b", protocol=SSOProtocol.OIDC,
        )
        assert p1 == p2

    def test_inequality(self):
        p1 = SSOProviderModel.reconstitute(
            id="abc", name="A", slug="a", protocol=SSOProtocol.SAML,
        )
        p2 = SSOProviderModel.reconstitute(
            id="xyz", name="A", slug="a", protocol=SSOProtocol.SAML,
        )
        assert p1 != p2

    def test_hash(self):
        p1 = SSOProviderModel.reconstitute(
            id="abc", name="A", slug="a", protocol=SSOProtocol.SAML,
        )
        p2 = SSOProviderModel.reconstitute(
            id="abc", name="B", slug="b", protocol=SSOProtocol.OIDC,
        )
        assert hash(p1) == hash(p2)


class TestSSOGlobalConfig:
    """測試 SSOGlobalConfig"""

    def test_default_values(self):
        config = SSOGlobalConfig()
        assert config.auto_create_users is False
        assert config.enforce_sso is False
        assert config.default_role == "NORMAL"

    def test_custom_values(self):
        config = SSOGlobalConfig(
            auto_create_users=True,
            enforce_sso=True,
            default_role="EMPLOYEE",
        )
        assert config.auto_create_users is True
        assert config.enforce_sso is True
        assert config.default_role == "EMPLOYEE"

    def test_update(self):
        config = SSOGlobalConfig()
        config.update(auto_create_users=True, enforce_sso=True, default_role="EMPLOYEE")
        assert config.auto_create_users is True
        assert config.enforce_sso is True
        assert config.default_role == "EMPLOYEE"

    def test_update_partial(self):
        config = SSOGlobalConfig()
        config.update(auto_create_users=True)
        assert config.auto_create_users is True
        assert config.enforce_sso is False
        assert config.default_role == "NORMAL"

    def test_update_invalid_role_raises(self):
        config = SSOGlobalConfig()
        with pytest.raises(ValueError, match="Default role must be one of"):
            config.update(default_role="ADMIN")


class TestSSOUserLink:
    """測試 SSOUserLink 值物件"""

    def test_creation(self):
        link = SSOUserLink(
            id="link-1",
            user_id="user-1",
            provider_id="provider-1",
            external_id="ext-id-123",
        )
        assert link.id == "link-1"
        assert link.user_id == "user-1"
        assert link.provider_id == "provider-1"
        assert link.external_id == "ext-id-123"
        assert link.created_at is None

    def test_is_frozen(self):
        link = SSOUserLink(
            id="link-1", user_id="user-1", provider_id="provider-1", external_id="ext-id-123"
        )
        with pytest.raises(AttributeError):
            link.id = "changed"
