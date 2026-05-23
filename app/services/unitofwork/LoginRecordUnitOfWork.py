from app.repositories.sqlalchemy.LoginRecordRepository import (
    LoginRecordRepository,
    LoginRecordQueryRepository,
)
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class LoginRecordUnitOfWork(BaseUnitOfWork):
    """Unit of Work for login-record write operations."""

    def _setup_repositories(self, session):
        self.repo = LoginRecordRepository(session)


class LoginRecordQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only login-record queries."""

    def _setup_repositories(self, session):
        self.query_repo = LoginRecordQueryRepository(session)
