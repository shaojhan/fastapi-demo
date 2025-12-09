from pydantic import (
    BaseModel as PydanticBaseModel,
    ConfigDict
    )
from datetime import datetime
from enum import Enum

from SpiffWorkflow.task import TaskState

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
    


    