from app.repositories.sqlalchemy.EmployeeRepository import EmployeeQueryRepository, EmployeeRepository
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class EmployeeUnitOfWork(BaseUnitOfWork):
    """Unit of Work for the Employee aggregate."""

    def _setup_repositories(self, session):
        self.repo = EmployeeRepository(session)


class EmployeeQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only employee queries."""

    def _setup_repositories(self, session):
        self.query_repo = EmployeeQueryRepository(session)
