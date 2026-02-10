from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.SSORepository import (
    SSOProviderRepository,
    SSOConfigRepository,
    SSOUserLinkRepository,
)
from app.repositories.sqlalchemy.UserRepository import UserRepository


class SSOUnitOfWork:
    """Unit of Work for SSO write operations."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.provider_repo = SSOProviderRepository(self.session)
        self.config_repo = SSOConfigRepository(self.session)
        self.user_link_repo = SSOUserLinkRepository(self.session)
        self.user_repo = UserRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()


class SSOQueryUnitOfWork:
    """Unit of Work for read-only SSO queries."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.provider_repo = SSOProviderRepository(self.session)
        self.config_repo = SSOConfigRepository(self.session)
        self.user_link_repo = SSOUserLinkRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
