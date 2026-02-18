from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.LoginRecordRepository import (
    LoginRecordRepository,
    LoginRecordQueryRepository,
)


class LoginRecordUnitOfWork:
    def __init__(self):
        self.session_factory = sessionmaker(engine, expire_on_commit=False)

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = LoginRecordRepository(self.session)
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


class LoginRecordQueryUnitOfWork:
    def __init__(self):
        self.session_factory = sessionmaker(engine, expire_on_commit=False)

    def __enter__(self):
        self.session = self.session_factory()
        self.query_repo = LoginRecordQueryRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
