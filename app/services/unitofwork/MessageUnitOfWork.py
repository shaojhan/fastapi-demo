from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.MessageRepository import (
    MessageRepository,
    MessageQueryRepository
)


class MessageUnitOfWork:
    """Unit of Work for message write operations."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = MessageRepository(self.session)
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


class MessageQueryUnitOfWork:
    """Unit of Work for read-only message queries."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.query_repo = MessageQueryRepository(self.session)
        self.repo = MessageRepository(self.session)  # For query methods
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
