from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.UserRepository import UserRepository
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository


class AssignEmployeeUnitOfWork:
    """
    Unit of Work for cross-aggregate operations involving User and Employee.
    Provides both repositories sharing a single database session/transaction.
    """

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.user_repo = UserRepository(self.session)
        self.employee_repo = EmployeeRepository(self.session)
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
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self):
        """Rollback the current transaction."""
        self.session.rollback()
