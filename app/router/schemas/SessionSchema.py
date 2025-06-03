from pydantic import (
    BaseModel as PydanticBaseModel,
    ConfigDict
    )
from datetime import datetime

class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

class SessionCreate(BaseModel):
    user_id: str
    expire_at: datetime

class SessionRead(BaseModel):
    id: str
    user_id: str
    expire_at: datetime
