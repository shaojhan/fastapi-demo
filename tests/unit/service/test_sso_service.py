"""
Unit tests for SSOAdminService and SSOService.
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.SSOAdminService import SSOAdminService
from app.services.SSOService import SSOService
from app.domain.SSOModel import (
    SSOProviderModel,
    SSOProtocol,
    SAMLConfig,
    OIDCConfig,
    AttributeMapping,
    SSOGlobalConfig,
    SSOUserLink,
)
from app.domain.UserModel import UserModel, UserRole
from app.domain.services.AuthenticationService import AuthToken
from app.exceptions.SSOException import (
    SSOProviderNotFoundError,
    SSOProviderSlugExistsError,
    SSOProviderNameExistsError,
    SSOProviderInactiveError,
    SSOUserNotAllowedError,
    SSOStateInvalidError,
)


# --- Test Data ---
TEST_PROVIDER_ID = str(uuid4())
TEST_USER_ID = str(uuid4())

SAML_CONFIG_DICT = {
    "idp_entity_id": "https://okta.example.com/saml",
    "idp_sso_url": "https://okta.example.com/sso",
    "idp_x509_cert": "MIICpDCCAYwCCQD...",
    "sp_entity_id": "https://myapp.example.com/saml",
    "sp_acs_url": "https://myapp.example.com/api/sso/saml/okta/acs",
}

OIDC_CONFIG_DICT = {
    "client_id": "my-client-id",
    "client_secret": "my-client-secret",
    "authorization_url": "https://azure.example.com/authorize",
    "token_url": "https://azure.example.com/token",
}


def _make_provider(
    provider_id=None,
    name="Okta",
    slug="okta",
    protocol=SSOProtocol.SAML,
    is_active=False,
) -> SSOProviderModel:
    saml = SAMLConfig(**SAML_CONFIG_DICT) if protocol == SSOProtocol.SAML else None
    oidc = OIDCConfig(**OIDC_CONFIG_DICT) if protocol == SSOProtocol.OIDC else None
    return SSOProviderModel.reconstitute(
        id=provider_id or TEST_PROVIDER_ID,
        name=name,
        slug=slug,
        protocol=protocol,
        saml_config=saml,
        oidc_config=oidc,
        is_active=is_active,
        display_order=0,
        created_at=datetime.now(),
    )


def _make_user(user_id=None) -> UserModel:
    from app.domain.UserModel import Profile, HashedPassword
    return UserModel(
        id=user_id or TEST_USER_ID,
        uid="testuser",
        email="test@example.com",
        hashed_password=HashedPassword("hashed"),
        profile=Profile(name="Test User"),
        role=UserRole.NORMAL,
        email_verified=True,
    )


# ===== SSOAdminService Tests =====

class TestSSOAdminServiceCreateProvider:
    """Tests for SSOAdminService.create_provider"""

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_create_saml_provider(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_slug.return_value = None
        mock_uow.provider_repo.get_by_name.return_value = None
        mock_uow.provider_repo.add.side_effect = lambda p: p

        service = SSOAdminService()
        result = service.create_provider(
            name="Okta",
            slug="okta",
            protocol="SAML",
            saml_config=SAML_CONFIG_DICT,
        )

        assert result.name == "Okta"
        assert result.protocol == SSOProtocol.SAML
        mock_uow.provider_repo.add.assert_called_once()

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_create_provider_slug_exists(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_slug.return_value = _make_provider()

        service = SSOAdminService()
        with pytest.raises(SSOProviderSlugExistsError):
            service.create_provider(name="New", slug="okta", protocol="SAML", saml_config=SAML_CONFIG_DICT)

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_create_provider_name_exists(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_slug.return_value = None
        mock_uow.provider_repo.get_by_name.return_value = _make_provider()

        service = SSOAdminService()
        with pytest.raises(SSOProviderNameExistsError):
            service.create_provider(name="Okta", slug="new-slug", protocol="SAML", saml_config=SAML_CONFIG_DICT)


class TestSSOAdminServiceGetProvider:
    """Tests for SSOAdminService.get_provider"""

    @patch("app.services.SSOAdminService.SSOQueryUnitOfWork")
    def test_get_provider(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_uow.provider_repo.get_by_id.return_value = provider

        service = SSOAdminService()
        result = service.get_provider(TEST_PROVIDER_ID)
        assert result.id == TEST_PROVIDER_ID

    @patch("app.services.SSOAdminService.SSOQueryUnitOfWork")
    def test_get_provider_not_found(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_id.return_value = None

        service = SSOAdminService()
        with pytest.raises(SSOProviderNotFoundError):
            service.get_provider(str(uuid4()))


class TestSSOAdminServiceListProviders:
    """Tests for SSOAdminService.list_providers"""

    @patch("app.services.SSOAdminService.SSOQueryUnitOfWork")
    def test_list_providers(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_all.return_value = [_make_provider()]

        service = SSOAdminService()
        result = service.list_providers()
        assert len(result) == 1


class TestSSOAdminServiceUpdateProvider:
    """Tests for SSOAdminService.update_provider"""

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_update_provider(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_uow.provider_repo.get_by_id.return_value = provider
        mock_uow.provider_repo.get_by_name.return_value = None
        mock_uow.provider_repo.update.side_effect = lambda p: p

        service = SSOAdminService()
        result = service.update_provider(TEST_PROVIDER_ID, name="New Name")
        assert result.name == "New Name"

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_update_provider_not_found(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_id.return_value = None

        service = SSOAdminService()
        with pytest.raises(SSOProviderNotFoundError):
            service.update_provider(str(uuid4()), name="New")


class TestSSOAdminServiceDeleteProvider:
    """Tests for SSOAdminService.delete_provider"""

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_delete_provider(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_id.return_value = _make_provider()
        mock_uow.provider_repo.delete.return_value = True

        service = SSOAdminService()
        service.delete_provider(TEST_PROVIDER_ID)
        mock_uow.provider_repo.delete.assert_called_once_with(TEST_PROVIDER_ID)

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_delete_provider_not_found(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_id.return_value = None

        service = SSOAdminService()
        with pytest.raises(SSOProviderNotFoundError):
            service.delete_provider(str(uuid4()))


class TestSSOAdminServiceActivateDeactivate:
    """Tests for activate/deactivate provider"""

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_activate_provider(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider(is_active=False)
        mock_uow.provider_repo.get_by_id.return_value = provider
        mock_uow.provider_repo.update.side_effect = lambda p: p

        service = SSOAdminService()
        result = service.activate_provider(TEST_PROVIDER_ID)
        assert result.is_active is True

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_deactivate_provider(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider(is_active=True)
        mock_uow.provider_repo.get_by_id.return_value = provider
        mock_uow.provider_repo.update.side_effect = lambda p: p

        service = SSOAdminService()
        result = service.deactivate_provider(TEST_PROVIDER_ID)
        assert result.is_active is False


class TestSSOAdminServiceConfig:
    """Tests for SSO config operations"""

    @patch("app.services.SSOAdminService.SSOQueryUnitOfWork")
    def test_get_config(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.config_repo.get_config.return_value = SSOGlobalConfig()

        service = SSOAdminService()
        result = service.get_config()
        assert result.auto_create_users is False

    @patch("app.services.SSOAdminService.SSOUnitOfWork")
    def test_update_config(self, mock_uow_class):
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        config = SSOGlobalConfig()
        mock_uow.config_repo.get_config.return_value = config
        mock_uow.config_repo.save_config.side_effect = lambda c: c

        service = SSOAdminService()
        result = service.update_config(auto_create_users=True, enforce_sso=True)
        assert result.auto_create_users is True
        assert result.enforce_sso is True


# ===== SSOService Tests =====

class TestSSOServiceListActiveProviders:
    """Tests for SSOService.list_active_providers"""

    @patch("app.services.SSOService.SSOQueryUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_list_active_providers(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_active.return_value = [_make_provider(is_active=True)]

        service = SSOService()
        result = service.list_active_providers()
        assert len(result) == 1


class TestSSOServiceInitiateLogin:
    """Tests for SSOService.initiate_login"""

    @patch("app.services.SSOService.SSOQueryUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_initiate_oidc_login(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api"
        )
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider(protocol=SSOProtocol.OIDC, slug="azure", is_active=True)
        mock_uow.provider_repo.get_by_slug.return_value = provider

        service = SSOService()
        result = service.initiate_login("azure")
        assert "redirect_url" in result
        assert "authorize" in result["redirect_url"]

    @patch("app.services.SSOService.SSOQueryUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_initiate_login_not_found(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_slug.return_value = None

        service = SSOService()
        with pytest.raises(SSOProviderNotFoundError):
            service.initiate_login("nonexistent")

    @patch("app.services.SSOService.SSOQueryUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_initiate_login_inactive(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.provider_repo.get_by_slug.return_value = _make_provider(is_active=False)

        service = SSOService()
        with pytest.raises(SSOProviderInactiveError):
            service.initiate_login("okta")


class TestSSOServiceAuthenticateUser:
    """Tests for SSOService._authenticate_sso_user"""

    @patch("app.services.SSOService.SSOUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_authenticate_existing_link(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        user = _make_user()
        link = SSOUserLink(
            id=str(uuid4()), user_id=TEST_USER_ID,
            provider_id=TEST_PROVIDER_ID, external_id="ext-123"
        )
        mock_uow.user_link_repo.get_by_provider_and_external_id.return_value = link
        mock_uow.user_repo.get_by_id.return_value = user
        mock_uow.config_repo.get_config.return_value = SSOGlobalConfig()

        service = SSOService()
        provider = _make_provider()
        token, returned_user = service._authenticate_sso_user(
            provider, "ext-123", "test@example.com", "Test User"
        )
        assert returned_user.id == TEST_USER_ID
        assert token.access_token is not None

    @patch("app.services.SSOService.SSOUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_authenticate_link_by_email(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        user = _make_user()
        mock_uow.user_link_repo.get_by_provider_and_external_id.return_value = None
        mock_uow.user_repo.get_by_email.return_value = user
        mock_uow.config_repo.get_config.return_value = SSOGlobalConfig()

        service = SSOService()
        provider = _make_provider()
        token, returned_user = service._authenticate_sso_user(
            provider, "ext-456", "test@example.com", "Test User"
        )
        assert returned_user.id == TEST_USER_ID
        mock_uow.user_link_repo.add.assert_called_once()

    @patch("app.services.SSOService.SSOUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_authenticate_auto_create_disabled(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_uow.user_link_repo.get_by_provider_and_external_id.return_value = None
        mock_uow.user_repo.get_by_email.return_value = None
        mock_uow.config_repo.get_config.return_value = SSOGlobalConfig(auto_create_users=False)

        service = SSOService()
        provider = _make_provider()
        with pytest.raises(SSOUserNotAllowedError):
            service._authenticate_sso_user(
                provider, "ext-789", "new@example.com", "New User"
            )

    @patch("app.services.SSOService.SSOUnitOfWork")
    @patch("app.services.SSOService.get_settings")
    def test_authenticate_auto_create_enabled(self, mock_settings, mock_uow_class):
        mock_settings.return_value = MagicMock(SSO_STATE_SECRET="test-secret", SSO_CALLBACK_BASE_URL="http://localhost:8000/api")
        mock_uow = MagicMock()
        mock_uow_class.return_value.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow_class.return_value.__exit__ = MagicMock(return_value=False)

        user = _make_user()
        mock_uow.user_link_repo.get_by_provider_and_external_id.return_value = None
        mock_uow.user_repo.get_by_email.side_effect = [None, user]  # First None, then created
        mock_uow.user_repo.exists_by_uid.return_value = False
        mock_uow.config_repo.get_config.return_value = SSOGlobalConfig(
            auto_create_users=True, default_role="NORMAL"
        )

        service = SSOService()
        provider = _make_provider()
        token, returned_user = service._authenticate_sso_user(
            provider, "ext-new", "new@example.com", "New User"
        )
        assert returned_user is not None
        mock_uow.user_repo.add.assert_called_once()


class TestSSOServiceStateManagement:
    """Tests for state generation and verification"""

    @patch("app.services.SSOService.get_settings")
    def test_generate_and_verify_state(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api"
        )
        service = SSOService()

        state = service._generate_state(TEST_PROVIDER_ID)
        result = service._verify_state(state)
        assert result == TEST_PROVIDER_ID

    @patch("app.services.SSOService.get_settings")
    def test_verify_invalid_state(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api"
        )
        service = SSOService()

        result = service._verify_state("invalid-state")
        assert result is None

    @patch("app.services.SSOService.get_settings")
    def test_verify_tampered_state(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api"
        )
        service = SSOService()

        state = service._generate_state(TEST_PROVIDER_ID)
        # Tamper with the signature
        parts = state.split(":")
        parts[2] = "tampered"
        tampered = ":".join(parts)

        result = service._verify_state(tampered)
        assert result is None


class TestSSOServiceAuthCodeFlow:
    """Tests for authorization code create and exchange."""

    @patch("app.services.SSOService.get_settings")
    def test_create_and_exchange_code(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api",
        )
        service = SSOService()
        user = _make_user()
        token = AuthToken(access_token="jwt-token", token_type="bearer", expires_in=3600)

        code = service._create_auth_code(token, user)
        assert isinstance(code, str)
        assert len(code) > 0

        returned_token, returned_user = service.exchange_code(code)
        assert returned_token.access_token == "jwt-token"
        assert returned_user.id == user.id

    @patch("app.services.SSOService.get_settings")
    def test_exchange_invalid_code(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api",
        )
        service = SSOService()

        with pytest.raises(SSOStateInvalidError):
            service.exchange_code("nonexistent-code")

    @patch("app.services.SSOService.get_settings")
    def test_exchange_code_only_once(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api",
        )
        service = SSOService()
        user = _make_user()
        token = AuthToken(access_token="jwt-token", token_type="bearer", expires_in=3600)

        code = service._create_auth_code(token, user)
        service.exchange_code(code)

        # Second exchange should fail
        with pytest.raises(SSOStateInvalidError):
            service.exchange_code(code)

    @patch("app.services.SSOService._auth_codes", {})
    @patch("app.services.SSOService.get_settings")
    def test_exchange_expired_code(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api",
        )
        service = SSOService()
        user = _make_user()
        token = AuthToken(access_token="jwt-token", token_type="bearer", expires_in=3600)

        code = service._create_auth_code(token, user)

        # Manually expire the code
        from app.services.SSOService import _auth_codes
        _auth_codes[code]["created_at"] = time.time() - 120  # 2 minutes ago

        with pytest.raises(SSOStateInvalidError):
            service.exchange_code(code)

    @patch("app.services.SSOService.get_settings")
    def test_cleanup_expired_codes(self, mock_settings):
        mock_settings.return_value = MagicMock(
            SSO_STATE_SECRET="test-secret",
            SSO_CALLBACK_BASE_URL="http://localhost:8000/api",
        )
        service = SSOService()

        from app.services.SSOService import _auth_codes

        # Add an expired entry
        _auth_codes["expired-code"] = {
            "token": MagicMock(),
            "user": MagicMock(),
            "created_at": time.time() - 120,
        }

        service._cleanup_expired_codes()
        assert "expired-code" not in _auth_codes
