from app.repositories.sqlalchemy.KafkaRepository import KafkaMessageRepository
from app.services.unitofwork.base import BaseUnitOfWork


class KafkaUnitOfWork(BaseUnitOfWork):
    """Unit of Work for Kafka message operations."""

    def _setup_repositories(self, session):
        self.repo = KafkaMessageRepository(session)
