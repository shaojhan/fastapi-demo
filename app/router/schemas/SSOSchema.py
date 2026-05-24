from datetime import datetime
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# === Request Schema ===

class SAMLConfigRequest(BaseModel):
    """SAML IdP configuration."""
    idp_entity_id: str = Field(..., description='IdP Entity ID')
    idp_sso_url: str = Field(..., description='IdP SSO URL')
    idp_x509_cert: str = Field(..., description='IdP X.509 Certificate')
    sp_entity_id: str = Field(..., description='SP Entity ID')
    sp_acs_url: str = Field(..., description='SP ACS URL')
    idp_slo_url: str | None = Field(None, description='IdP SLO URL')


class OIDCConfigRequest(BaseModel):
    """OIDC configuration."""
    client_id: str = Field(..., description='OIDC Client ID')
    client_secret: str = Field(..., description='OIDC Client Secret')
    authorization_url: str = Field(..., description='Authorization URL')
    token_url: str = Field(..., description='Token URL')
    userinfo_url: str | None = Field(None, description='UserInfo URL')
    jwks_uri: str | None = Field(None, description='JWKS URI')
    scopes: str = Field('openid email profile', description='Scopes')


class AttributeMappingRequest(BaseModel):
    """Attribute mapping configuration."""
    email: str = Field('email', description='Email attribute name')
    name: str = Field('name', description='Name attribute name')
    external_id: str = Field('sub', description='External ID attribute name')


class CreateSSOProviderRequest(BaseModel):
    """Request to create an SSO provider."""
    name: str = Field(..., min_length=1, max_length=128, description='Provider display name')
    slug: str = Field(..., min_length=1, max_length=64, description='URL-friendly identifier')
    protocol: str = Field(..., description='Protocol: SAML or OIDC')
    saml_config: SAMLConfigRequest | None = Field(None, description='SAML configuration')
    oidc_config: OIDCConfigRequest | None = Field(None, description='OIDC configuration')
    attribute_mapping: AttributeMappingRequest | None = Field(None, description='Attribute mapping')
    display_order: int = Field(0, description='Display order on login page')


class UpdateSSOProviderRequest(BaseModel):
    """Request to update an SSO provider."""
    name: str | None = Field(None, min_length=1, max_length=128, description='Provider display name')
    saml_config: SAMLConfigRequest | None = Field(None, description='SAML configuration')
    oidc_config: OIDCConfigRequest | None = Field(None, description='OIDC configuration')
    attribute_mapping: AttributeMappingRequest | None = Field(None, description='Attribute mapping')
    display_order: int | None = Field(None, description='Display order')


class UpdateSSOConfigRequest(BaseModel):
    """Request to update global SSO configuration."""
    auto_create_users: bool | None = Field(None, description='Auto-create users on SSO login')
    enforce_sso: bool | None = Field(None, description='Enforce SSO (disable password login)')
    default_role: str | None = Field(None, description='Default role for auto-created users')


# === Response Schema ===

class SAMLConfigResponse(BaseModel):
    """SAML configuration in response."""
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None = None
    sp_entity_id: str
    sp_acs_url: str


class OIDCConfigResponse(BaseModel):
    """OIDC configuration in response (secrets hidden)."""
    client_id: str
    authorization_url: str
    token_url: str
    userinfo_url: str | None = None
    jwks_uri: str | None = None
    scopes: str


class AttributeMappingResponse(BaseModel):
    """Attribute mapping in response."""
    email: str = 'email'
    name: str = 'name'
    external_id: str = 'sub'


class SSOProviderResponse(BaseModel):
    """Full SSO provider response."""
    id: UUID
    name: str
    slug: str
    protocol: str
    saml_config: SAMLConfigResponse | None = None
    oidc_config: OIDCConfigResponse | None = None
    attribute_mapping: AttributeMappingResponse
    is_active: bool
    display_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SSOProviderListItem(BaseModel):
    """SSO provider list item (public)."""
    name: str
    slug: str
    protocol: str


class SSOProviderListResponse(BaseModel):
    """List of active SSO providers."""
    providers: list[SSOProviderListItem]


class SSOAdminProviderListResponse(BaseModel):
    """Admin list of all SSO providers."""
    providers: list[SSOProviderResponse]


class SSOConfigResponse(BaseModel):
    """Global SSO configuration response."""
    auto_create_users: bool = False
    enforce_sso: bool = False
    default_role: str = 'NORMAL'


class SSOLoginResponse(BaseModel):
    """SSO login initiation response."""
    redirect_url: str


class SSOExchangeCodeRequest(BaseModel):
    """Request to exchange authorization code for token."""
    code: str = Field(..., description='Authorization code from SSO callback')


class SSOTokenResponse(BaseModel):
    """Token response after code exchange."""
    access_token: str
    token_type: str = 'bearer'
    expires_in: int


class SSOActionResponse(BaseModel):
    """Action result response."""
    message: str
    success: bool = True
