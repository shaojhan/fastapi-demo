from app.repositories.sqlalchemy.MQTTRepository import MQTTMessageRepository
from app.services.unitofwork.base import BaseUnitOfWork


class MQTTUnitOfWork(BaseUnitOfWork):
    """Unit of Work for MQTT message operations."""

    def _setup_repositories(self, session):
        self.repo = MQTTMessageRepository(session)
