from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.ApprovalRepository import (
    ApprovalRepository,
    ApprovalQueryRepository,
)
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository


class ApprovalUnitOfWork:
    """Unit of Work for approval write operations."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = ApprovalRepository(self.session)
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
        self.session.commit()

    def rollback(self):
        self.session.rollback()


class ApprovalQueryUnitOfWork:
    """Unit of Work for read-only approval queries."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = ApprovalQueryRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
