"""
SSO Authentication Service.

Handles SP-initiated login flows for SAML 2.0 and OIDC.
Manages user provisioning and linking after successful SSO authentication.
"""
import hashlib
import hmac
import secrets
import time
from datetime import date
from urllib.parse import urlencode
from uuid import uuid4

from passlib.context import CryptContext

from app.config import get_settings
from app.domain.SSOModel import (
    SSOProviderModel,
    SSOProtocol,
    SSOUserLink,
    AttributeMapping,
)
from app.domain.UserModel import UserModel, UserRole
from app.domain.services.AuthenticationService import AuthToken, AuthenticationDomainService
from app.exceptions.SSOException import (
    SSOProviderNotFoundError,
    SSOProviderInactiveError,
    SSOAuthenticationError,
    SSOUserNotAllowedError,
    SSOCallbackError,
    SSOStateInvalidError,
)
from app.services.unitofwork.SSOUnitOfWork import SSOUnitOfWork, SSOQueryUnitOfWork

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# State TTL in seconds
STATE_TTL = 300  # 5 minutes

# Authorization code TTL in seconds
AUTH_CODE_TTL = 60  # 1 minute

# In-memory store for authorization codes (use Redis in production)
_auth_codes: dict[str, dict] = {}


class SSOService:
    """Application service for SSO authentication flows."""

    def __init__(self):
        self._settings = get_settings()
        self._auth_domain_service = AuthenticationDomainService()

    def list_active_providers(self) -> list[SSOProviderModel]:
        with SSOQueryUnitOfWork() as uow:
            return uow.provider_repo.get_active()

    def initiate_login(self, slug: str) -> dict:
        """
        Initiate an SSO login flow.

        Args:
            slug: The provider slug

        Returns:
            Dict with redirect_url for the client

        Raises:
            SSOProviderNotFoundError: Provider not found
            SSOProviderInactiveError: Provider is inactive
        """
        with SSOQueryUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_slug(slug)
            if not provider:
                raise SSOProviderNotFoundError()
            if not provider.is_active:
                raise SSOProviderInactiveError()

        if provider.protocol == SSOProtocol.OIDC:
            return self._initiate_oidc_login(provider)
        else:
            return self._initiate_saml_login(provider)

    def handle_oidc_callback(self, slug: str, code: str, state: str) -> str:
        """
        Handle OIDC callback after IdP authentication.

        Args:
            slug: Provider slug
            code: Authorization code from IdP
            state: State parameter for CSRF

        Returns:
            Short-lived authorization code for the frontend to exchange
        """
        # Validate state
        provider_id = self._verify_state(state)
        if not provider_id:
            raise SSOStateInvalidError()

        with SSOQueryUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_slug(slug)
            if not provider:
                raise SSOProviderNotFoundError()
            if provider.id != provider_id:
                raise SSOStateInvalidError()

        try:
            # Exchange code for tokens
            import httpx
            resp = httpx.post(
                provider.oidc_config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._get_oidc_callback_url(slug),
                    "client_id": provider.oidc_config.client_id,
                    "client_secret": provider.oidc_config.client_secret,
                },
            )
            resp.raise_for_status()
            tokens = resp.json()

            # Get user info
            access_token = tokens["access_token"]

            if provider.oidc_config.userinfo_url:
                resp = httpx.get(
                    provider.oidc_config.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                user_info = resp.json()
            else:
                # Decode ID token (basic parsing)
                import json
                import base64
                id_token = tokens.get("id_token", "")
                parts = id_token.split(".")
                if len(parts) < 2:
                    raise SSOCallbackError(message="Invalid ID token")
                payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
                user_info = json.loads(base64.urlsafe_b64decode(payload))

        except SSOCallbackError:
            raise
        except Exception as e:
            raise SSOCallbackError(message=f"OIDC callback failed: {str(e)}")

        # Extract user attributes
        mapping = provider.attribute_mapping
        external_id = str(user_info.get(mapping.external_id, ""))
        email = user_info.get(mapping.email, "")
        name = user_info.get(mapping.name, "")

        if not external_id or not email:
            raise SSOAuthenticationError(message="Missing required user attributes from IdP")

        token, user = self._authenticate_sso_user(provider, external_id, email, name)
        return self._create_auth_code(token, user)

    def handle_saml_callback(self, slug: str, saml_response: str) -> str:
        """
        Handle SAML ACS callback.

        Args:
            slug: Provider slug
            saml_response: Base64-encoded SAML Response

        Returns:
            Short-lived authorization code for the frontend to exchange
        """
        with SSOQueryUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_slug(slug)
            if not provider:
                raise SSOProviderNotFoundError()
            if not provider.is_active:
                raise SSOProviderInactiveError()

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            from onelogin.saml2.utils import OneLogin_Saml2_Utils

            saml_settings = self._build_saml_settings(provider)
            auth = OneLogin_Saml2_Auth(
                {"post_data": {"SAMLResponse": saml_response}, "http_host": "", "script_name": ""},
                old_settings=saml_settings,
            )
            auth.process_response()

            if auth.get_errors():
                raise SSOCallbackError(
                    message=f"SAML validation failed: {', '.join(auth.get_errors())}"
                )

            attributes = auth.get_attributes()
            name_id = auth.get_nameid()

        except SSOCallbackError:
            raise
        except ImportError:
            raise SSOCallbackError(message="python3-saml is not installed")
        except Exception as e:
            raise SSOCallbackError(message=f"SAML callback failed: {str(e)}")

        mapping = provider.attribute_mapping
        external_id = name_id or ""
        email = ""
        name = ""

        if attributes:
            email_attrs = attributes.get(mapping.email, [])
            email = email_attrs[0] if email_attrs else ""
            name_attrs = attributes.get(mapping.name, [])
            name = name_attrs[0] if name_attrs else ""

        if not external_id or not email:
            raise SSOAuthenticationError(message="Missing required user attributes from IdP")

        token, user = self._authenticate_sso_user(provider, external_id, email, name)
        return self._create_auth_code(token, user)

    def exchange_code(self, code: str) -> tuple[AuthToken, UserModel]:
        """
        Exchange a short-lived authorization code for an access token.

        Args:
            code: The authorization code from SSO callback

        Returns:
            Tuple of (AuthToken, UserModel)

        Raises:
            SSOStateInvalidError: If code is invalid or expired
        """
        auth_data = _auth_codes.pop(code, None)
        if not auth_data:
            raise SSOStateInvalidError(message="Invalid or expired authorization code")

        # Check TTL
        if time.time() - auth_data["created_at"] > AUTH_CODE_TTL:
            raise SSOStateInvalidError(message="Authorization code has expired")

        return auth_data["token"], auth_data["user"]

    def _create_auth_code(self, token: AuthToken, user: UserModel) -> str:
        """
        Create a short-lived authorization code that maps to a token + user.

        Returns:
            The authorization code string
        """
        code = secrets.token_urlsafe(32)
        _auth_codes[code] = {
            "token": token,
            "user": user,
            "created_at": time.time(),
        }
        # Cleanup expired codes (simple housekeeping)
        self._cleanup_expired_codes()
        return code

    @staticmethod
    def _cleanup_expired_codes() -> None:
        """Remove expired authorization codes."""
        now = time.time()
        expired = [k for k, v in _auth_codes.items() if now - v["created_at"] > AUTH_CODE_TTL]
        for k in expired:
            _auth_codes.pop(k, None)

    def get_saml_metadata(self, slug: str) -> str:
        """
        Generate SP metadata XML for a SAML provider.

        Args:
            slug: Provider slug

        Returns:
            SP metadata XML string
        """
        with SSOQueryUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_slug(slug)
            if not provider:
                raise SSOProviderNotFoundError()

        try:
            from onelogin.saml2.settings import OneLogin_Saml2_Settings
            saml_settings = OneLogin_Saml2_Settings(
                settings=self._build_saml_settings(provider),
                sp_validation_only=True,
            )
            return saml_settings.get_sp_metadata()
        except ImportError:
            raise SSOCallbackError(message="python3-saml is not installed")

    def _authenticate_sso_user(
        self,
        provider: SSOProviderModel,
        external_id: str,
        email: str,
        name: str,
    ) -> tuple[AuthToken, UserModel]:
        """
        Find or create a user from SSO attributes, then return a JWT.

        Flow:
        1. Find by sso_user_links (provider_id, external_id) → existing link
        2. Find by email → create link
        3. auto_create_users=True → create user + link
        4. auto_create_users=False → reject
        """
        with SSOUnitOfWork() as uow:
            config = uow.config_repo.get_config()

            # 1. Check existing SSO link
            link = uow.user_link_repo.get_by_provider_and_external_id(
                provider.id, external_id
            )
            if link:
                user = uow.user_repo.get_by_id(link.user_id)
                if user:
                    token = self._auth_domain_service.create_token(user.id, user.uid)
                    return token, user

            # 2. Check by email
            user = uow.user_repo.get_by_email(email)
            if user:
                new_link = SSOUserLink(
                    id=str(uuid4()),
                    user_id=user.id,
                    provider_id=provider.id,
                    external_id=external_id,
                )
                uow.user_link_repo.add(new_link)
                uow.commit()
                token = self._auth_domain_service.create_token(user.id, user.uid)
                return token, user

            # 3. Auto-create user if enabled
            if not config.auto_create_users:
                raise SSOUserNotAllowedError()

            # Generate unique uid
            uid = self._generate_unique_uid(email, uow)
            dummy_password = pwd_context.hash(secrets.token_urlsafe(32))

            role = config.default_role
            user_dict = {
                "id": uuid4(),
                "uid": uid,
                "email": email,
                "pwd": dummy_password,
                "role": role,
                "email_verified": True,
            }
            profile_dict = {
                "name": name or uid,
                "birthdate": date(2000, 1, 1),
                "description": "",
            }
            uow.user_repo.add(user_dict, profile_dict)
            uow.commit()

            user = uow.user_repo.get_by_email(email)
            new_link = SSOUserLink(
                id=str(uuid4()),
                user_id=user.id,
                provider_id=provider.id,
                external_id=external_id,
            )
            uow.user_link_repo.add(new_link)
            uow.commit()

            token = self._auth_domain_service.create_token(user.id, user.uid)
            return token, user

    def _initiate_oidc_login(self, provider: SSOProviderModel) -> dict:
        state = self._generate_state(provider.id)
        params = {
            "client_id": provider.oidc_config.client_id,
            "redirect_uri": self._get_oidc_callback_url(provider.slug),
            "response_type": "code",
            "scope": provider.oidc_config.scopes,
            "state": state,
        }
        redirect_url = f"{provider.oidc_config.authorization_url}?{urlencode(params)}"
        return {"redirect_url": redirect_url}

    def _initiate_saml_login(self, provider: SSOProviderModel) -> dict:
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            saml_settings = self._build_saml_settings(provider)
            auth = OneLogin_Saml2_Auth(
                {"http_host": "", "script_name": ""},
                old_settings=saml_settings,
            )
            redirect_url = auth.login()
            return {"redirect_url": redirect_url}
        except ImportError:
            # Fallback: redirect directly to IdP SSO URL
            return {"redirect_url": provider.saml_config.idp_sso_url}

    def _build_saml_settings(self, provider: SSOProviderModel) -> dict:
        saml = provider.saml_config
        return {
            "strict": True,
            "sp": {
                "entityId": saml.sp_entity_id,
                "assertionConsumerService": {
                    "url": saml.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
            },
            "idp": {
                "entityId": saml.idp_entity_id,
                "singleSignOnService": {
                    "url": saml.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": saml.idp_x509_cert,
            },
        }

    def _get_oidc_callback_url(self, slug: str) -> str:
        base = self._settings.SSO_CALLBACK_BASE_URL
        return f"{base}/sso/oidc/{slug}/callback"

    def _generate_state(self, provider_id: str) -> str:
        """Generate HMAC-signed state with timestamp."""
        timestamp = str(int(time.time()))
        payload = f"{provider_id}:{timestamp}"
        secret = self._settings.SSO_STATE_SECRET
        signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}:{signature}"

    def _verify_state(self, state: str) -> str | None:
        """Verify state and return provider_id if valid."""
        try:
            parts = state.split(":")
            if len(parts) != 3:
                return None

            provider_id, timestamp, signature = parts

            # Verify TTL
            if time.time() - int(timestamp) > STATE_TTL:
                return None

            # Verify signature
            payload = f"{provider_id}:{timestamp}"
            secret = self._settings.SSO_STATE_SECRET
            expected = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                return None

            return provider_id
        except Exception:
            return None

    @staticmethod
    def _generate_unique_uid(email: str, uow) -> str:
        base_uid = email.split("@")[0]
        uid = base_uid
        counter = 1
        while uow.user_repo.exists_by_uid(uid):
            uid = f"{base_uid}_{counter}"
            counter += 1
        return uid
