from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field

from app.domain.ApprovalModel import ApprovalStatus, ApprovalType, LeaveType


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# === Request Schemas ===

class CreateLeaveRequest(BaseModel):
    """Request schema for creating a leave approval request."""
    leave_type: LeaveType = Field(..., description='Type of leave')
    start_date: datetime = Field(..., description='Leave start date/time')
    end_date: datetime = Field(..., description='Leave end date/time')
    reason: str = Field(..., min_length=1, max_length=500, description='Reason for leave')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'leave_type': 'ANNUAL',
                    'start_date': '2026-03-01T09:00:00',
                    'end_date': '2026-03-03T18:00:00',
                    'reason': '家庭旅遊',
                }
            ]
        }
    }


class CreateExpenseRequest(BaseModel):
    """Request schema for creating an expense approval request."""
    amount: float = Field(..., gt=0, description='Expense amount')
    category: str = Field(..., min_length=1, max_length=100, description='Expense category')
    description: str = Field(..., min_length=1, max_length=500, description='Expense description')
    receipt_url: str | None = Field(None, max_length=512, description='Receipt URL')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'amount': 1500.0,
                    'category': '交通費',
                    'description': '出差計程車費',
                    'receipt_url': None,
                }
            ]
        }
    }


class ApproveRejectRequest(BaseModel):
    """Request schema for approving or rejecting a request."""
    comment: str | None = Field(None, max_length=500, description='Approval/rejection comment')


# === Response Schemas ===

class ApprovalStepResponse(BaseModel):
    """Response schema for an approval step."""
    step_order: int
    approver_id: str
    approver_name: str | None = None
    approver_department: str | None = None
    approver_role_name: str | None = None
    approver_role_level: int | None = None
    status: ApprovalStatus
    comment: str | None = None
    decided_at: datetime | None = None
    created_at: datetime | None = None


class ApprovalRequestResponse(BaseModel):
    """Response schema for a full approval request with steps."""
    id: str
    type: ApprovalType
    status: ApprovalStatus
    requester_id: str
    detail: dict
    steps: list[ApprovalStepResponse]
    current_step_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApprovalListItem(BaseModel):
    """Response schema for an approval request in a list."""
    id: str
    type: ApprovalType
    status: ApprovalStatus
    requester_id: str
    created_at: datetime | None = None
    current_step_order: int | None = None


class ApprovalListResponse(BaseModel):
    """Paginated list of approval requests."""
    items: list[ApprovalListItem]
    total: int
    page: int
    size: int
