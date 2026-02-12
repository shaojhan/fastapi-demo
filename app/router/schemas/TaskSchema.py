from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class TaskSubmitResponse(TaskBaseModel):
    task_id: str = Field(..., description="Background task ID for polling status")


class TaskProgressInfo(TaskBaseModel):
    current: int = Field(0, description="Current item being processed")
    total: int = Field(0, description="Total items to process")
    percent: float = Field(0.0, description="Completion percentage")
    current_idno: str | None = Field(None, description="Current item identifier")


class TaskStatusResponse(TaskBaseModel):
    task_id: str
    status: str = Field(..., description="PENDING | STARTED | PROGRESS | SUCCESS | FAILURE | REVOKED")
    progress: TaskProgressInfo | None = Field(None, description="Progress info (when status is PROGRESS)")
    result: Any | None = Field(None, description="Task result (when status is SUCCESS)")
    error: str | None = Field(None, description="Error message (when status is FAILURE)")


class TaskCancelResponse(TaskBaseModel):
    task_id: str
    cancelled: bool
