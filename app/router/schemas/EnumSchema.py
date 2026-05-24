from enum import Enum

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)





class ProjectStateEnum(str, Enum):
    """

    """

    ADDED = 'ADDED'
    IN_APPROVAL = 'IN_APPROVAL'
    APPROVAL = 'APPROVAL'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'
    IN_PRODUCTION = 'IN_PRODUCTION'
    COMPLETED = 'COMPLETED'