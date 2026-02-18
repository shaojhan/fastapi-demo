import uuid
from datetime import datetime, timezone


class LoginRecordModel:
    def __init__(
        self,
        id: str,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        created_at: datetime,
        user_id: str | None = None,
        failure_reason: str | None = None,
    ):
        self._id = id
        self._user_id = user_id
        self._username = username
        self._ip_address = ip_address
        self._user_agent = user_agent
        self._success = success
        self._failure_reason = failure_reason
        self._created_at = created_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def user_id(self) -> str | None:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def ip_address(self) -> str:
        return self._ip_address

    @property
    def user_agent(self) -> str:
        return self._user_agent

    @property
    def success(self) -> bool:
        return self._success

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @staticmethod
    def create(
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        user_id: str | None = None,
        failure_reason: str | None = None,
    ) -> "LoginRecordModel":
        return LoginRecordModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def reconstitute(
        id: str,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        created_at: datetime,
        user_id: str | None = None,
        failure_reason: str | None = None,
    ) -> "LoginRecordModel":
        return LoginRecordModel(
            id=id,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            created_at=created_at,
        )
