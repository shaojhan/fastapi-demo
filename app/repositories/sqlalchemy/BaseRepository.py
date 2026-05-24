from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass

class BaseRepository:
    def __init__(self, db: Session):
        self.db = db