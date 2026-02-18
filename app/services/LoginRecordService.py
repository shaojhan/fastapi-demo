from uuid import UUID

from app.domain.LoginRecordModel import LoginRecordModel
from app.services.unitofwork.LoginRecordUnitOfWork import (
    LoginRecordUnitOfWork,
    LoginRecordQueryUnitOfWork,
)


class LoginRecordService:

    def record_login(
        self,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        user_id: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        record = LoginRecordModel.create(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            user_id=user_id,
            failure_reason=failure_reason,
        )
        with LoginRecordUnitOfWork() as uow:
            uow.repo.add({
                "id": UUID(record.id),
                "user_id": UUID(record.user_id) if record.user_id else None,
                "username": record.username,
                "ip_address": record.ip_address,
                "user_agent": record.user_agent,
                "success": record.success,
                "failure_reason": record.failure_reason,
            })


class LoginRecordQueryService:

    def get_my_records(
        self, user_id: str, page: int, size: int
    ) -> tuple[list[LoginRecordModel], int]:
        with LoginRecordQueryUnitOfWork() as uow:
            return uow.query_repo.get_by_user_id(user_id, page, size)

    def get_all_records(
        self, page: int, size: int, user_id: str | None = None
    ) -> tuple[list[LoginRecordModel], int]:
        with LoginRecordQueryUnitOfWork() as uow:
            return uow.query_repo.get_all(page, size, user_id)
