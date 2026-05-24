from app.repositories.sqlalchemy.SSORepository import (
    SSOConfigRepository,
    SSOProviderRepository,
    SSOUserLinkRepository,
)
from app.repositories.sqlalchemy.UserRepository import UserRepository
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class SSOUnitOfWork(BaseUnitOfWork):
    """Unit of Work for SSO write operations."""

    def _setup_repositories(self, session):
        self.provider_repo = SSOProviderRepository(session)
        self.config_repo = SSOConfigRepository(session)
        self.user_link_repo = SSOUserLinkRepository(session)
        self.user_repo = UserRepository(session)


class SSOQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only SSO queries."""

    def _setup_repositories(self, session):
        self.provider_repo = SSOProviderRepository(session)
        self.config_repo = SSOConfigRepository(session)
        self.user_link_repo = SSOUserLinkRepository(session)
