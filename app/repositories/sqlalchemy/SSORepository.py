from typing import Optional, List
from uuid import UUID

from .BaseRepository import BaseRepository
from database.models.sso import SSOProvider, SSOConfig, SSOUserLink, SSOProtocol
from app.domain.SSOModel import (
    SSOProviderModel,
    SSOProtocol as DomainProtocol,
    SAMLConfig,
    OIDCConfig,
    AttributeMapping,
    SSOGlobalConfig,
    SSOUserLink as DomainUserLink,
)


class SSOProviderRepository(BaseRepository):
    """Repository for SSO Provider aggregate persistence operations."""

    def add(self, provider: SSOProviderModel) -> SSOProviderModel:
        entity = SSOProvider(
            id=UUID(provider.id),
            name=provider.name,
            slug=provider.slug,
            protocol=SSOProtocol(provider.protocol.value),
            # SAML
            idp_entity_id=provider.saml_config.idp_entity_id if provider.saml_config else None,
            idp_sso_url=provider.saml_config.idp_sso_url if provider.saml_config else None,
            idp_slo_url=provider.saml_config.idp_slo_url if provider.saml_config else None,
            idp_x509_cert=provider.saml_config.idp_x509_cert if provider.saml_config else None,
            sp_entity_id=provider.saml_config.sp_entity_id if provider.saml_config else None,
            sp_acs_url=provider.saml_config.sp_acs_url if provider.saml_config else None,
            # OIDC
            client_id=provider.oidc_config.client_id if provider.oidc_config else None,
            client_secret=provider.oidc_config.client_secret if provider.oidc_config else None,
            authorization_url=provider.oidc_config.authorization_url if provider.oidc_config else None,
            token_url=provider.oidc_config.token_url if provider.oidc_config else None,
            userinfo_url=provider.oidc_config.userinfo_url if provider.oidc_config else None,
            jwks_uri=provider.oidc_config.jwks_uri if provider.oidc_config else None,
            scopes=provider.oidc_config.scopes if provider.oidc_config else None,
            # Common
            attribute_mapping=provider.attribute_mapping.to_dict(),
            is_active=provider.is_active,
            display_order=provider.display_order,
        )

        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return self._to_domain_model(entity)

    def get_by_id(self, provider_id: str) -> Optional[SSOProviderModel]:
        entity = self.db.query(SSOProvider).filter(
            SSOProvider.id == UUID(provider_id)
        ).first()
        if not entity:
            return None
        return self._to_domain_model(entity)

    def get_by_slug(self, slug: str) -> Optional[SSOProviderModel]:
        entity = self.db.query(SSOProvider).filter(
            SSOProvider.slug == slug
        ).first()
        if not entity:
            return None
        return self._to_domain_model(entity)

    def get_by_name(self, name: str) -> Optional[SSOProviderModel]:
        entity = self.db.query(SSOProvider).filter(
            SSOProvider.name == name
        ).first()
        if not entity:
            return None
        return self._to_domain_model(entity)

    def get_all(self) -> List[SSOProviderModel]:
        entities = self.db.query(SSOProvider).order_by(
            SSOProvider.display_order.asc(),
            SSOProvider.name.asc(),
        ).all()
        return [self._to_domain_model(e) for e in entities]

    def get_active(self) -> List[SSOProviderModel]:
        entities = self.db.query(SSOProvider).filter(
            SSOProvider.is_active == True
        ).order_by(
            SSOProvider.display_order.asc(),
            SSOProvider.name.asc(),
        ).all()
        return [self._to_domain_model(e) for e in entities]

    def update(self, provider: SSOProviderModel) -> SSOProviderModel:
        entity = self.db.query(SSOProvider).filter(
            SSOProvider.id == UUID(provider.id)
        ).first()

        if not entity:
            raise ValueError(f"SSO Provider with ID {provider.id} not found")

        entity.name = provider.name
        entity.is_active = provider.is_active
        entity.display_order = provider.display_order
        entity.attribute_mapping = provider.attribute_mapping.to_dict()

        if provider.protocol == DomainProtocol.SAML and provider.saml_config:
            entity.idp_entity_id = provider.saml_config.idp_entity_id
            entity.idp_sso_url = provider.saml_config.idp_sso_url
            entity.idp_slo_url = provider.saml_config.idp_slo_url
            entity.idp_x509_cert = provider.saml_config.idp_x509_cert
            entity.sp_entity_id = provider.saml_config.sp_entity_id
            entity.sp_acs_url = provider.saml_config.sp_acs_url

        if provider.protocol == DomainProtocol.OIDC and provider.oidc_config:
            entity.client_id = provider.oidc_config.client_id
            entity.client_secret = provider.oidc_config.client_secret
            entity.authorization_url = provider.oidc_config.authorization_url
            entity.token_url = provider.oidc_config.token_url
            entity.userinfo_url = provider.oidc_config.userinfo_url
            entity.jwks_uri = provider.oidc_config.jwks_uri
            entity.scopes = provider.oidc_config.scopes

        self.db.flush()
        self.db.refresh(entity)
        return self._to_domain_model(entity)

    def delete(self, provider_id: str) -> bool:
        entity = self.db.query(SSOProvider).filter(
            SSOProvider.id == UUID(provider_id)
        ).first()
        if not entity:
            return False
        self.db.delete(entity)
        self.db.flush()
        return True

    def _to_domain_model(self, entity: SSOProvider) -> SSOProviderModel:
        protocol = DomainProtocol(entity.protocol.value)

        saml_config = None
        if protocol == DomainProtocol.SAML and entity.idp_entity_id:
            saml_config = SAMLConfig(
                idp_entity_id=entity.idp_entity_id,
                idp_sso_url=entity.idp_sso_url,
                idp_x509_cert=entity.idp_x509_cert,
                sp_entity_id=entity.sp_entity_id,
                sp_acs_url=entity.sp_acs_url,
                idp_slo_url=entity.idp_slo_url,
            )

        oidc_config = None
        if protocol == DomainProtocol.OIDC and entity.client_id:
            oidc_config = OIDCConfig(
                client_id=entity.client_id,
                client_secret=entity.client_secret,
                authorization_url=entity.authorization_url,
                token_url=entity.token_url,
                userinfo_url=entity.userinfo_url,
                jwks_uri=entity.jwks_uri,
                scopes=entity.scopes or "openid email profile",
            )

        return SSOProviderModel.reconstitute(
            id=str(entity.id),
            name=entity.name,
            slug=entity.slug,
            protocol=protocol,
            saml_config=saml_config,
            oidc_config=oidc_config,
            attribute_mapping=AttributeMapping.from_dict(entity.attribute_mapping),
            is_active=entity.is_active,
            display_order=entity.display_order,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class SSOConfigRepository(BaseRepository):
    """Repository for SSO global configuration (singleton)."""

    def get_config(self) -> SSOGlobalConfig:
        entity = self.db.query(SSOConfig).first()
        if not entity:
            return SSOGlobalConfig()
        return SSOGlobalConfig(
            auto_create_users=entity.auto_create_users,
            enforce_sso=entity.enforce_sso,
            default_role=entity.default_role,
        )

    def save_config(self, config: SSOGlobalConfig) -> SSOGlobalConfig:
        entity = self.db.query(SSOConfig).first()
        if entity:
            entity.auto_create_users = config.auto_create_users
            entity.enforce_sso = config.enforce_sso
            entity.default_role = config.default_role
        else:
            entity = SSOConfig(
                auto_create_users=config.auto_create_users,
                enforce_sso=config.enforce_sso,
                default_role=config.default_role,
            )
            self.db.add(entity)

        self.db.flush()
        self.db.refresh(entity)
        return SSOGlobalConfig(
            auto_create_users=entity.auto_create_users,
            enforce_sso=entity.enforce_sso,
            default_role=entity.default_role,
        )


class SSOUserLinkRepository(BaseRepository):
    """Repository for SSO user links."""

    def add(self, user_link: DomainUserLink) -> DomainUserLink:
        entity = SSOUserLink(
            id=UUID(user_link.id),
            user_id=UUID(user_link.user_id),
            provider_id=UUID(user_link.provider_id),
            external_id=user_link.external_id,
        )
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return self._to_domain(entity)

    def get_by_provider_and_external_id(
        self, provider_id: str, external_id: str
    ) -> Optional[DomainUserLink]:
        entity = self.db.query(SSOUserLink).filter(
            SSOUserLink.provider_id == UUID(provider_id),
            SSOUserLink.external_id == external_id,
        ).first()
        if not entity:
            return None
        return self._to_domain(entity)

    def get_by_user_id(self, user_id: str) -> List[DomainUserLink]:
        entities = self.db.query(SSOUserLink).filter(
            SSOUserLink.user_id == UUID(user_id)
        ).all()
        return [self._to_domain(e) for e in entities]

    def delete_by_user_and_provider(self, user_id: str, provider_id: str) -> bool:
        entity = self.db.query(SSOUserLink).filter(
            SSOUserLink.user_id == UUID(user_id),
            SSOUserLink.provider_id == UUID(provider_id),
        ).first()
        if not entity:
            return False
        self.db.delete(entity)
        self.db.flush()
        return True

    def _to_domain(self, entity: SSOUserLink) -> DomainUserLink:
        return DomainUserLink(
            id=str(entity.id),
            user_id=str(entity.user_id),
            provider_id=str(entity.provider_id),
            external_id=entity.external_id,
            created_at=entity.created_at,
        )
