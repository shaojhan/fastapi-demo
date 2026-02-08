from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.ScheduleRepository import (
    ScheduleRepository,
    GoogleCalendarConfigRepository
)


class ScheduleUnitOfWork:
    """Unit of Work for schedule write operations."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = ScheduleRepository(self.session)
        self.google_config_repo = GoogleCalendarConfigRepository(self.session)
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


class ScheduleQueryUnitOfWork:
    """Unit of Work for read-only schedule queries."""

    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = ScheduleRepository(self.session)
        self.google_config_repo = GoogleCalendarConfigRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
