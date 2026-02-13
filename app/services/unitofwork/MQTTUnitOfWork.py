from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.MQTTRepository import MQTTMessageRepository


class MQTTUnitOfWork:
    """Unit of Work for MQTT message operations."""

    def __init__(self):
        self.session_factory = sessionmaker(engine, expire_on_commit=False)

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = MQTTMessageRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.session.rollback()
        finally:
            self.session.close()

    def commit(self):
        self.session.commit()
