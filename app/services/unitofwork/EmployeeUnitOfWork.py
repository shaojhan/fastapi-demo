from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository, EmployeeQueryRepository


class EmployeeUnitOfWork:
    """
    Unit of Work pattern for Employee aggregate.
    Manages database transactions and provides repository access.
    """

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = EmployeeRepository(self.session)
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


class EmployeeQueryUnitOfWork:
    """
    Unit of Work for read-only employee queries.
    Provides optimized query repository access.
    """

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.query_repo = EmployeeQueryRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
