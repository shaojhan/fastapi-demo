from pydantic import (
    BaseModel as PydanticBaseModel,
    ConfigDict,
    Field
    )
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional

from app.domain.EmployeeModel import Department


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class EmployeeLevelEnum(int, Enum):
    """
    PRESIDENT: 社長
    VICE_PRESIDENT: 副社長
    DIRECTOR: 部長
    MANAGER: 課長
    CHEIF: 組長
    STAFF: 普通員工
    """
    PRESIDENT = 32
    VICE_PRESIDENT = 16
    DIRECTOR = 8
    MANAGER = 4
    CHIEF = 2
    STAFF = 1


class AssignEmployeeRequest(BaseModel):
    """Request schema for assigning a user as an employee."""
    user_id: UUID = Field(..., description='使用者 UUID')
    idno: str = Field(..., description='員工編號', examples=['EMP001'])
    department: Department = Field(..., description='部門', examples=[Department.IT])
    role_id: int = Field(..., description='角色 ID', examples=[1])


class RoleInfoResponse(BaseModel):
    """Response schema for role information."""
    id: int
    name: str
    level: int
    authorities: list[str]


class AssignEmployeeResponse(BaseModel):
    """Response schema for a successfully assigned employee."""
    id: int = Field(description='Employee database ID')
    idno: str = Field(description='員工編號')
    department: Department = Field(description='部門')
    user_id: Optional[UUID] = Field(default=None, description='使用者 UUID')
    role: Optional[RoleInfoResponse] = Field(default=None, description='角色資訊')
    created_at: Optional[datetime] = Field(default=None, description='建立時間')
