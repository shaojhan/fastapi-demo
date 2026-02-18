from typing import Optional
from uuid import UUID

from .BaseRepository import BaseRepository
from database.models.login_record import LoginRecord
from app.domain.LoginRecordModel import LoginRecordModel


class LoginRecordRepository(BaseRepository):

    def add(self, record_dict: dict) -> LoginRecord:
        record = LoginRecord(**record_dict)
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record


class LoginRecordQueryRepository(BaseRepository):

    def get_by_user_id(
        self, user_id: str, page: int, size: int
    ) -> tuple[list[LoginRecordModel], int]:
        query = self.db.query(LoginRecord).filter(
            LoginRecord.user_id == UUID(user_id)
        )
        total = query.count()
        records = (
            query.order_by(LoginRecord.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return [self._to_domain_model(r) for r in records], total

    def get_all(
        self, page: int, size: int, user_id: str | None = None
    ) -> tuple[list[LoginRecordModel], int]:
        query = self.db.query(LoginRecord)
        if user_id:
            query = query.filter(LoginRecord.user_id == UUID(user_id))
        total = query.count()
        records = (
            query.order_by(LoginRecord.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return [self._to_domain_model(r) for r in records], total

    def _to_domain_model(self, record: LoginRecord) -> LoginRecordModel:
        return LoginRecordModel.reconstitute(
            id=str(record.id),
            user_id=str(record.user_id) if record.user_id else None,
            username=record.username,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            success=record.success,
            failure_reason=record.failure_reason,
            created_at=record.created_at,
        )
