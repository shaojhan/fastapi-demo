from fastapi import APIRouter, Depends, Query, Form
from fastapi.responses import RedirectResponse
from uuid import UUID

from app.router.schemas.SSOSchema import (
    CreateSSOProviderRequest,
    UpdateSSOProviderRequest,
    UpdateSSOConfigRequest,
    SSOProviderResponse,
    SSOProviderListItem,
    SSOProviderListResponse,
    SSOAdminProviderListResponse,
    SSOConfigResponse,
    SSOLoginResponse,
    SSOExchangeCodeRequest,
    SSOTokenResponse,
    SSOActionResponse,
    SAMLConfigResponse,
    OIDCConfigResponse,
    AttributeMappingResponse,
)
from app.services.SSOAdminService import SSOAdminService
from app.services.SSOService import SSOService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_admin
from app.config import get_settings


router = APIRouter(prefix='/sso', tags=['sso'])


def get_sso_admin_service() -> SSOAdminService:
    return SSOAdminService()


def get_sso_service() -> SSOService:
    return SSOService()


def _to_provider_response(provider) -> SSOProviderResponse:
    """Convert domain model to response."""
    saml = None
    if provider.saml_config:
        saml = SAMLConfigResponse(
            idp_entity_id=provider.saml_config.idp_entity_id,
            idp_sso_url=provider.saml_config.idp_sso_url,
            idp_slo_url=provider.saml_config.idp_slo_url,
            sp_entity_id=provider.saml_config.sp_entity_id,
            sp_acs_url=provider.saml_config.sp_acs_url,
        )

    oidc = None
    if provider.oidc_config:
        oidc = OIDCConfigResponse(
            client_id=provider.oidc_config.client_id,
            authorization_url=provider.oidc_config.authorization_url,
            token_url=provider.oidc_config.token_url,
            userinfo_url=provider.oidc_config.userinfo_url,
            jwks_uri=provider.oidc_config.jwks_uri,
            scopes=provider.oidc_config.scopes,
        )

    return SSOProviderResponse(
        id=UUID(provider.id),
        name=provider.name,
        slug=provider.slug,
        protocol=provider.protocol.value,
        saml_config=saml,
        oidc_config=oidc,
        attribute_mapping=AttributeMappingResponse(
            email=provider.attribute_mapping.email,
            name=provider.attribute_mapping.name,
            external_id=provider.attribute_mapping.external_id,
        ),
        is_active=provider.is_active,
        display_order=provider.display_order,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


# ===== Public endpoints =====

@router.get('/providers', response_model=SSOProviderListResponse, operation_id='list_sso_providers')
async def list_providers(
    service: SSOService = Depends(get_sso_service),
) -> SSOProviderListResponse:
    """List active SSO providers (for login page)."""
    providers = service.list_active_providers()
    items = [
        SSOProviderListItem(
            name=p.name,
            slug=p.slug,
            protocol=p.protocol.value,
        )
        for p in providers
    ]
    return SSOProviderListResponse(providers=items)


@router.get('/login/{slug}', response_model=SSOLoginResponse, operation_id='sso_login')
async def sso_login(
    slug: str,
    service: SSOService = Depends(get_sso_service),
) -> SSOLoginResponse:
    """Initiate SSO login. Redirects to IdP."""
    result = service.initiate_login(slug)
    return SSOLoginResponse(redirect_url=result["redirect_url"])


@router.get('/oidc/{slug}/callback', operation_id='oidc_callback')
async def oidc_callback(
    slug: str,
    code: str = Query(..., description='Authorization code from IdP'),
    state: str = Query(..., description='State for CSRF protection'),
    service: SSOService = Depends(get_sso_service),
):
    """OIDC callback endpoint. Redirects to frontend with a short-lived authorization code."""
    settings = get_settings()
    try:
        auth_code = service.handle_oidc_callback(slug, code, state)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?code={auth_code}",
            status_code=302,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error={str(e)}",
            status_code=302,
        )


@router.post('/saml/{slug}/acs', operation_id='saml_acs')
async def saml_acs(
    slug: str,
    SAMLResponse: str = Form(...),
    service: SSOService = Depends(get_sso_service),
):
    """SAML ACS endpoint. Redirects to frontend with a short-lived authorization code."""
    settings = get_settings()
    try:
        auth_code = service.handle_saml_callback(slug, SAMLResponse)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?code={auth_code}",
            status_code=302,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error={str(e)}",
            status_code=302,
        )


@router.post('/token', response_model=SSOTokenResponse, operation_id='sso_exchange_code')
async def exchange_code(
    request_body: SSOExchangeCodeRequest,
    service: SSOService = Depends(get_sso_service),
) -> SSOTokenResponse:
    """Exchange a short-lived authorization code for an access token."""
    token, user = service.exchange_code(request_body.code)
    return SSOTokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
    )


@router.get('/saml/{slug}/metadata', operation_id='saml_metadata')
async def saml_metadata(
    slug: str,
    service: SSOService = Depends(get_sso_service),
):
    """Get SP SAML metadata XML."""
    from fastapi.responses import Response
    metadata_xml = service.get_saml_metadata(slug)
    return Response(content=metadata_xml, media_type="application/xml")


# ===== Admin endpoints =====

@router.get('/admin/providers', response_model=SSOAdminProviderListResponse, operation_id='admin_list_sso_providers')
async def admin_list_providers(
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOAdminProviderListResponse:
    """List all SSO providers (admin)."""
    providers = service.list_providers()
    return SSOAdminProviderListResponse(
        providers=[_to_provider_response(p) for p in providers]
    )


@router.post('/admin/providers', response_model=SSOProviderResponse, operation_id='admin_create_sso_provider')
async def admin_create_provider(
    request_body: CreateSSOProviderRequest,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOProviderResponse:
    """Create a new SSO provider."""
    provider = service.create_provider(
        name=request_body.name,
        slug=request_body.slug,
        protocol=request_body.protocol,
        saml_config=request_body.saml_config.model_dump() if request_body.saml_config else None,
        oidc_config=request_body.oidc_config.model_dump() if request_body.oidc_config else None,
        attribute_mapping=request_body.attribute_mapping.model_dump() if request_body.attribute_mapping else None,
        display_order=request_body.display_order,
    )
    return _to_provider_response(provider)


@router.get('/admin/providers/{provider_id}', response_model=SSOProviderResponse, operation_id='admin_get_sso_provider')
async def admin_get_provider(
    provider_id: str,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOProviderResponse:
    """Get an SSO provider detail."""
    provider = service.get_provider(provider_id)
    return _to_provider_response(provider)


@router.put('/admin/providers/{provider_id}', response_model=SSOProviderResponse, operation_id='admin_update_sso_provider')
async def admin_update_provider(
    provider_id: str,
    request_body: UpdateSSOProviderRequest,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOProviderResponse:
    """Update an SSO provider."""
    provider = service.update_provider(
        provider_id=provider_id,
        name=request_body.name,
        saml_config=request_body.saml_config.model_dump() if request_body.saml_config else None,
        oidc_config=request_body.oidc_config.model_dump() if request_body.oidc_config else None,
        attribute_mapping=request_body.attribute_mapping.model_dump() if request_body.attribute_mapping else None,
        display_order=request_body.display_order,
    )
    return _to_provider_response(provider)


@router.delete('/admin/providers/{provider_id}', response_model=SSOActionResponse, operation_id='admin_delete_sso_provider')
async def admin_delete_provider(
    provider_id: str,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOActionResponse:
    """Delete an SSO provider."""
    service.delete_provider(provider_id)
    return SSOActionResponse(message='SSO Provider deleted.')


@router.post('/admin/providers/{provider_id}/activate', response_model=SSOProviderResponse, operation_id='admin_activate_sso_provider')
async def admin_activate_provider(
    provider_id: str,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOProviderResponse:
    """Activate an SSO provider."""
    provider = service.activate_provider(provider_id)
    return _to_provider_response(provider)


@router.post('/admin/providers/{provider_id}/deactivate', response_model=SSOProviderResponse, operation_id='admin_deactivate_sso_provider')
async def admin_deactivate_provider(
    provider_id: str,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOProviderResponse:
    """Deactivate an SSO provider."""
    provider = service.deactivate_provider(provider_id)
    return _to_provider_response(provider)


@router.get('/admin/config', response_model=SSOConfigResponse, operation_id='admin_get_sso_config')
async def admin_get_config(
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOConfigResponse:
    """Get global SSO configuration."""
    config = service.get_config()
    return SSOConfigResponse(
        auto_create_users=config.auto_create_users,
        enforce_sso=config.enforce_sso,
        default_role=config.default_role,
    )


@router.put('/admin/config', response_model=SSOConfigResponse, operation_id='admin_update_sso_config')
async def admin_update_config(
    request_body: UpdateSSOConfigRequest,
    current_user: UserModel = Depends(require_admin),
    service: SSOAdminService = Depends(get_sso_admin_service),
) -> SSOConfigResponse:
    """Update global SSO configuration."""
    config = service.update_config(
        auto_create_users=request_body.auto_create_users,
        enforce_sso=request_body.enforce_sso,
        default_role=request_body.default_role,
    )
    return SSOConfigResponse(
        auto_create_users=config.auto_create_users,
        enforce_sso=config.enforce_sso,
        default_role=config.default_role,
    )
