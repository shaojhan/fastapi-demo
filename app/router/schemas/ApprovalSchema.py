from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from app.domain.ApprovalModel import ApprovalType, ApprovalStatus, LeaveType


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
    receipt_url: Optional[str] = Field(None, max_length=512, description='Receipt URL')

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
    comment: Optional[str] = Field(None, max_length=500, description='Approval/rejection comment')


# === Response Schemas ===

class ApprovalStepResponse(BaseModel):
    """Response schema for an approval step."""
    step_order: int
    approver_id: str
    status: ApprovalStatus
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ApprovalRequestResponse(BaseModel):
    """Response schema for a full approval request with steps."""
    id: str
    type: ApprovalType
    status: ApprovalStatus
    requester_id: str
    detail: dict
    steps: List[ApprovalStepResponse]
    current_step_order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApprovalListItem(BaseModel):
    """Response schema for an approval request in a list."""
    id: str
    type: ApprovalType
    status: ApprovalStatus
    requester_id: str
    created_at: Optional[datetime] = None
    current_step_order: Optional[int] = None


class ApprovalListResponse(BaseModel):
    """Paginated list of approval requests."""
    items: List[ApprovalListItem]
    total: int
    page: int
    size: int
