from sqlalchemy.orm import DeclarativeBase, Session
from redis.asyncio import Redis

class Base(DeclarativeBase):
    pass

class BaseRepository:
    def __init__(self, db: Session):
        self.db = db