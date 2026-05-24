from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository
from app.repositories.sqlalchemy.UserRepository import UserRepository
from app.services.unitofwork.base import BaseUnitOfWork


class AssignEmployeeUnitOfWork(BaseUnitOfWork):
    """
    Unit of Work for cross-aggregate operations involving User and Employee.
    Provides both repositories sharing a single database session/transaction.
    """

    def _setup_repositories(self, session):
        self.user_repo = UserRepository(session)
        self.employee_repo = EmployeeRepository(session)
