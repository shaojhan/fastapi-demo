from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.KafkaRepository import KafkaMessageRepository


class KafkaUnitOfWork:
    """Unit of Work for Kafka message operations."""

    def __init__(self):
        self.session_factory = sessionmaker(engine, expire_on_commit=False)

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = KafkaMessageRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.session.rollback()
        finally:
            self.session.close()

    def commit(self):
        self.session.commit()
