from app.repositories.sqlalchemy.ChatRepository import ChatRepository
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class ChatUnitOfWork(BaseUnitOfWork):
    """Unit of Work for chat write operations."""

    def _setup_repositories(self, session):
        self.repo = ChatRepository(session)


class ChatQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only chat queries."""

    def _setup_repositories(self, session):
        self.repo = ChatRepository(session)
