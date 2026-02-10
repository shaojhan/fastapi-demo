"""
SSO Admin Service.

Handles CRUD operations for SSO providers and global SSO configuration.
Only accessible by Admin users.
"""
from typing import List

from app.domain.SSOModel import (
    SSOProviderModel,
    SSOProtocol,
    SAMLConfig,
    OIDCConfig,
    AttributeMapping,
    SSOGlobalConfig,
)
from app.services.unitofwork.SSOUnitOfWork import SSOUnitOfWork, SSOQueryUnitOfWork
from app.exceptions.SSOException import (
    SSOProviderNotFoundError,
    SSOProviderSlugExistsError,
    SSOProviderNameExistsError,
)


class SSOAdminService:
    """Application service for SSO admin operations."""

    def create_provider(
        self,
        name: str,
        slug: str,
        protocol: str,
        saml_config: dict | None = None,
        oidc_config: dict | None = None,
        attribute_mapping: dict | None = None,
        display_order: int = 0,
    ) -> SSOProviderModel:
        with SSOUnitOfWork() as uow:
            # Check uniqueness
            if uow.provider_repo.get_by_slug(slug):
                raise SSOProviderSlugExistsError()
            if uow.provider_repo.get_by_name(name):
                raise SSOProviderNameExistsError()

            proto = SSOProtocol(protocol)

            saml = None
            if saml_config and proto == SSOProtocol.SAML:
                saml = SAMLConfig(**saml_config)

            oidc = None
            if oidc_config and proto == SSOProtocol.OIDC:
                oidc = OIDCConfig(**oidc_config)

            attr_map = AttributeMapping.from_dict(attribute_mapping)

            provider = SSOProviderModel.create(
                name=name,
                slug=slug,
                protocol=proto,
                saml_config=saml,
                oidc_config=oidc,
                attribute_mapping=attr_map,
                display_order=display_order,
            )

            return uow.provider_repo.add(provider)

    def get_provider(self, provider_id: str) -> SSOProviderModel:
        with SSOQueryUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_id(provider_id)
            if not provider:
                raise SSOProviderNotFoundError()
            return provider

    def list_providers(self) -> List[SSOProviderModel]:
        with SSOQueryUnitOfWork() as uow:
            return uow.provider_repo.get_all()

    def update_provider(
        self,
        provider_id: str,
        name: str | None = None,
        saml_config: dict | None = None,
        oidc_config: dict | None = None,
        attribute_mapping: dict | None = None,
        display_order: int | None = None,
    ) -> SSOProviderModel:
        with SSOUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_id(provider_id)
            if not provider:
                raise SSOProviderNotFoundError()

            # Check name uniqueness if changing
            if name and name != provider.name:
                existing = uow.provider_repo.get_by_name(name)
                if existing:
                    raise SSOProviderNameExistsError()

            saml = None
            if saml_config and provider.protocol == SSOProtocol.SAML:
                saml = SAMLConfig(**saml_config)

            oidc = None
            if oidc_config and provider.protocol == SSOProtocol.OIDC:
                oidc = OIDCConfig(**oidc_config)

            attr_map = AttributeMapping.from_dict(attribute_mapping) if attribute_mapping else None

            provider.update(
                name=name,
                saml_config=saml,
                oidc_config=oidc,
                attribute_mapping=attr_map,
                display_order=display_order,
            )

            return uow.provider_repo.update(provider)

    def delete_provider(self, provider_id: str) -> None:
        with SSOUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_id(provider_id)
            if not provider:
                raise SSOProviderNotFoundError()
            uow.provider_repo.delete(provider_id)

    def activate_provider(self, provider_id: str) -> SSOProviderModel:
        with SSOUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_id(provider_id)
            if not provider:
                raise SSOProviderNotFoundError()
            provider.activate()
            return uow.provider_repo.update(provider)

    def deactivate_provider(self, provider_id: str) -> SSOProviderModel:
        with SSOUnitOfWork() as uow:
            provider = uow.provider_repo.get_by_id(provider_id)
            if not provider:
                raise SSOProviderNotFoundError()
            provider.deactivate()
            return uow.provider_repo.update(provider)

    def get_config(self) -> SSOGlobalConfig:
        with SSOQueryUnitOfWork() as uow:
            return uow.config_repo.get_config()

    def update_config(
        self,
        auto_create_users: bool | None = None,
        enforce_sso: bool | None = None,
        default_role: str | None = None,
    ) -> SSOGlobalConfig:
        with SSOUnitOfWork() as uow:
            config = uow.config_repo.get_config()
            config.update(
                auto_create_users=auto_create_users,
                enforce_sso=enforce_sso,
                default_role=default_role,
            )
            return uow.config_repo.save_config(config)
