from app.repositories.sqlalchemy.UserRepository import UserRepository, UserQueryRepository
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class UserUnitOfWork(BaseUnitOfWork):
    """Unit of Work for user write operations."""

    def _setup_repositories(self, session):
        self.repo = UserRepository(session)


class UserQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only user queries."""

    def _setup_repositories(self, session):
        self.query_repo = UserQueryRepository(session)
