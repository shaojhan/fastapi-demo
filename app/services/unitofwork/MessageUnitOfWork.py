from app.repositories.sqlalchemy.MessageRepository import (
    MessageRepository,
    MessageQueryRepository,
)
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class MessageUnitOfWork(BaseUnitOfWork):
    """Unit of Work for message write operations."""

    def _setup_repositories(self, session):
        self.repo = MessageRepository(session)


class MessageQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only message queries."""

    def _setup_repositories(self, session):
        self.query_repo = MessageQueryRepository(session)
        self.repo = MessageRepository(session)  # For query methods
