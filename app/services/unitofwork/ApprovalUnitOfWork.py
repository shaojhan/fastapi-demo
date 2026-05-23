from app.repositories.sqlalchemy.ApprovalRepository import (
    ApprovalRepository,
    ApprovalQueryRepository,
)
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class ApprovalUnitOfWork(BaseUnitOfWork):
    """Unit of Work for approval write operations."""

    def _setup_repositories(self, session):
        self.repo = ApprovalRepository(session)
        self.employee_repo = EmployeeRepository(session)


class ApprovalQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only approval queries."""

    def _setup_repositories(self, session):
        self.repo = ApprovalQueryRepository(session)
