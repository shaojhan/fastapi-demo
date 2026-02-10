"""
Unit tests for SSO repositories.
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.repositories.sqlalchemy.SSORepository import (
    SSOProviderRepository,
    SSOConfigRepository,
    SSOUserLinkRepository,
)
from app.domain.SSOModel import (
    SSOProviderModel,
    SSOProtocol,
    SAMLConfig,
    OIDCConfig,
    AttributeMapping,
    SSOGlobalConfig,
    SSOUserLink as DomainUserLink,
)
from database.models.sso import SSOProvider, SSOConfig, SSOUserLink


# --- Test Data ---
SAML_CONFIG = SAMLConfig(
    idp_entity_id="https://okta.example.com/saml",
    idp_sso_url="https://okta.example.com/sso",
    idp_x509_cert="MIICpDCCAYwCCQD...",
    sp_entity_id="https://myapp.example.com/saml",
    sp_acs_url="https://myapp.example.com/api/sso/saml/okta/acs",
)

OIDC_CONFIG = OIDCConfig(
    client_id="my-client-id",
    client_secret="my-client-secret",
    authorization_url="https://azure.example.com/authorize",
    token_url="https://azure.example.com/token",
    userinfo_url="https://azure.example.com/userinfo",
)


def _create_saml_provider(name="Okta", slug="okta") -> SSOProviderModel:
    return SSOProviderModel.create(
        name=name,
        slug=slug,
        protocol=SSOProtocol.SAML,
        saml_config=SAML_CONFIG,
    )


def _create_oidc_provider(name="Azure AD", slug="azure-ad") -> SSOProviderModel:
    return SSOProviderModel.create(
        name=name,
        slug=slug,
        protocol=SSOProtocol.OIDC,
        oidc_config=OIDC_CONFIG,
    )


class TestSSOProviderRepository:
    """Tests for SSOProviderRepository"""

    def test_add_saml_provider(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        result = repo.add(provider)

        assert result.id == provider.id
        assert result.name == "Okta"
        assert result.slug == "okta"
        assert result.protocol == SSOProtocol.SAML
        assert result.saml_config is not None
        assert result.saml_config.idp_entity_id == SAML_CONFIG.idp_entity_id

    def test_add_oidc_provider(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_oidc_provider()
        result = repo.add(provider)

        assert result.protocol == SSOProtocol.OIDC
        assert result.oidc_config is not None
        assert result.oidc_config.client_id == "my-client-id"

    def test_get_by_id(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        repo.add(provider)
        test_db_session.commit()

        result = repo.get_by_id(provider.id)
        assert result is not None
        assert result.id == provider.id

    def test_get_by_id_not_found(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        result = repo.get_by_id(str(uuid4()))
        assert result is None

    def test_get_by_slug(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        repo.add(provider)
        test_db_session.commit()

        result = repo.get_by_slug("okta")
        assert result is not None
        assert result.slug == "okta"

    def test_get_by_name(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        repo.add(provider)
        test_db_session.commit()

        result = repo.get_by_name("Okta")
        assert result is not None
        assert result.name == "Okta"

    def test_get_all(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        repo.add(_create_saml_provider())
        repo.add(_create_oidc_provider())
        test_db_session.commit()

        results = repo.get_all()
        assert len(results) == 2

    def test_get_active(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        p1 = _create_saml_provider()
        p1.activate()
        repo.add(p1)

        p2 = _create_oidc_provider()
        repo.add(p2)
        test_db_session.commit()

        results = repo.get_active()
        assert len(results) == 1
        assert results[0].is_active is True

    def test_update(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        repo.add(provider)
        test_db_session.commit()

        provider.update(name="Okta Enterprise")
        result = repo.update(provider)
        assert result.name == "Okta Enterprise"

    def test_delete(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        repo.add(provider)
        test_db_session.commit()

        result = repo.delete(provider.id)
        assert result is True

        assert repo.get_by_id(provider.id) is None

    def test_delete_not_found(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        result = repo.delete(str(uuid4()))
        assert result is False

    def test_get_all_ordered(self, test_db_session):
        repo = SSOProviderRepository(test_db_session)
        p1 = _create_saml_provider(name="Zeta", slug="zeta")
        p1.update(display_order=2)
        repo.add(p1)

        p2 = _create_oidc_provider(name="Alpha", slug="alpha")
        p2.update(display_order=1)
        repo.add(p2)
        test_db_session.commit()

        results = repo.get_all()
        assert results[0].display_order <= results[1].display_order


class TestSSOConfigRepository:
    """Tests for SSOConfigRepository"""

    def test_get_config_default(self, test_db_session):
        repo = SSOConfigRepository(test_db_session)
        config = repo.get_config()
        assert config.auto_create_users is False
        assert config.enforce_sso is False
        assert config.default_role == "NORMAL"

    def test_save_config(self, test_db_session):
        repo = SSOConfigRepository(test_db_session)
        config = SSOGlobalConfig(auto_create_users=True, enforce_sso=True, default_role="EMPLOYEE")
        result = repo.save_config(config)
        test_db_session.commit()

        assert result.auto_create_users is True
        assert result.enforce_sso is True
        assert result.default_role == "EMPLOYEE"

    def test_update_config(self, test_db_session):
        repo = SSOConfigRepository(test_db_session)
        # Create initial
        repo.save_config(SSOGlobalConfig())
        test_db_session.commit()

        # Update
        config = SSOGlobalConfig(auto_create_users=True, enforce_sso=False, default_role="NORMAL")
        result = repo.save_config(config)
        assert result.auto_create_users is True

    def test_get_config_after_save(self, test_db_session):
        repo = SSOConfigRepository(test_db_session)
        repo.save_config(SSOGlobalConfig(auto_create_users=True, enforce_sso=True))
        test_db_session.commit()

        config = repo.get_config()
        assert config.auto_create_users is True
        assert config.enforce_sso is True


class TestSSOUserLinkRepository:
    """Tests for SSOUserLinkRepository"""

    def test_add_link(self, test_db_session, sample_users):
        provider_repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        provider_repo.add(provider)
        test_db_session.commit()

        link_repo = SSOUserLinkRepository(test_db_session)
        user = sample_users[0]
        link = DomainUserLink(
            id=str(uuid4()),
            user_id=str(user.id),
            provider_id=provider.id,
            external_id="ext-user-123",
        )
        result = link_repo.add(link)
        assert result.external_id == "ext-user-123"
        assert result.user_id == str(user.id)
        assert result.provider_id == provider.id

    def test_get_by_provider_and_external_id(self, test_db_session, sample_users):
        provider_repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        provider_repo.add(provider)
        test_db_session.commit()

        link_repo = SSOUserLinkRepository(test_db_session)
        user = sample_users[0]
        link = DomainUserLink(
            id=str(uuid4()),
            user_id=str(user.id),
            provider_id=provider.id,
            external_id="ext-user-123",
        )
        link_repo.add(link)
        test_db_session.commit()

        result = link_repo.get_by_provider_and_external_id(provider.id, "ext-user-123")
        assert result is not None
        assert result.external_id == "ext-user-123"

    def test_get_by_provider_and_external_id_not_found(self, test_db_session):
        link_repo = SSOUserLinkRepository(test_db_session)
        result = link_repo.get_by_provider_and_external_id(str(uuid4()), "nonexistent")
        assert result is None

    def test_get_by_user_id(self, test_db_session, sample_users):
        provider_repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        provider_repo.add(provider)
        test_db_session.commit()

        link_repo = SSOUserLinkRepository(test_db_session)
        user = sample_users[0]
        link = DomainUserLink(
            id=str(uuid4()),
            user_id=str(user.id),
            provider_id=provider.id,
            external_id="ext-user-123",
        )
        link_repo.add(link)
        test_db_session.commit()

        results = link_repo.get_by_user_id(str(user.id))
        assert len(results) == 1

    def test_delete_by_user_and_provider(self, test_db_session, sample_users):
        provider_repo = SSOProviderRepository(test_db_session)
        provider = _create_saml_provider()
        provider_repo.add(provider)
        test_db_session.commit()

        link_repo = SSOUserLinkRepository(test_db_session)
        user = sample_users[0]
        link = DomainUserLink(
            id=str(uuid4()),
            user_id=str(user.id),
            provider_id=provider.id,
            external_id="ext-user-123",
        )
        link_repo.add(link)
        test_db_session.commit()

        result = link_repo.delete_by_user_and_provider(str(user.id), provider.id)
        assert result is True

        remaining = link_repo.get_by_user_id(str(user.id))
        assert len(remaining) == 0

    def test_delete_by_user_and_provider_not_found(self, test_db_session):
        link_repo = SSOUserLinkRepository(test_db_session)
        result = link_repo.delete_by_user_and_provider(str(uuid4()), str(uuid4()))
        assert result is False
