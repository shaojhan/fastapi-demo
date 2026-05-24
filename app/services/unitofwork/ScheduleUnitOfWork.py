from app.repositories.sqlalchemy.ScheduleRepository import (
    GoogleCalendarConfigRepository,
    ScheduleRepository,
)
from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class ScheduleUnitOfWork(BaseUnitOfWork):
    """Unit of Work for schedule write operations."""

    def _setup_repositories(self, session):
        self.repo = ScheduleRepository(session)
        self.google_config_repo = GoogleCalendarConfigRepository(session)


class ScheduleQueryUnitOfWork(BaseQueryUnitOfWork):
    """Unit of Work for read-only schedule queries."""

    def _setup_repositories(self, session):
        self.repo = ScheduleRepository(session)
        self.google_config_repo = GoogleCalendarConfigRepository(session)
