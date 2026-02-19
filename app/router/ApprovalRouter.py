from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.router.schemas.ApprovalSchema import (
    CreateLeaveRequest,
    CreateExpenseRequest,
    ApproveRejectRequest,
    ApprovalRequestResponse,
    ApprovalStepResponse,
    ApprovalListItem,
    ApprovalListResponse,
)
from app.services.ApprovalService import ApprovalService, ApprovalQueryService
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalStatus,
    LeaveDetail,
    ExpenseDetail,
)
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_employee


router = APIRouter(prefix='/approvals', tags=['approval'])


def get_approval_service() -> ApprovalService:
    return ApprovalService()


def get_approval_query_service() -> ApprovalQueryService:
    return ApprovalQueryService()


def _to_response(request: ApprovalRequest) -> ApprovalRequestResponse:
    current = request.current_step()
    return ApprovalRequestResponse(
        id=request.id,
        type=request.type,
        status=request.status,
        requester_id=request.requester_id,
        detail=request.detail_dict(),
        steps=[
            ApprovalStepResponse(
                step_order=s.step_order,
                approver_id=s.approver_id,
                status=s.status,
                comment=s.comment,
                decided_at=s.decided_at,
                created_at=s.created_at,
            )
            for s in request.steps
        ],
        current_step_order=current.step_order if current else None,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _to_list_item(request: ApprovalRequest) -> ApprovalListItem:
    current = request.current_step()
    return ApprovalListItem(
        id=request.id,
        type=request.type,
        status=request.status,
        requester_id=request.requester_id,
        created_at=request.created_at,
        current_step_order=current.step_order if current else None,
    )


@router.post('/leave', response_model=ApprovalRequestResponse, operation_id='create_leave_request')
async def create_leave_request(
    request_body: CreateLeaveRequest,
    current_user: UserModel = Depends(require_employee),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Create a leave approval request."""
    detail = LeaveDetail(
        leave_type=request_body.leave_type,
        start_date=request_body.start_date,
        end_date=request_body.end_date,
        reason=request_body.reason,
    )
    result = service.create_leave_request(
        requester_id=current_user.id,
        detail=detail,
    )
    return _to_response(result)


@router.post('/expense', response_model=ApprovalRequestResponse, operation_id='create_expense_request')
async def create_expense_request(
    request_body: CreateExpenseRequest,
    current_user: UserModel = Depends(require_employee),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Create an expense approval request."""
    detail = ExpenseDetail(
        amount=request_body.amount,
        category=request_body.category,
        description=request_body.description,
        receipt_url=request_body.receipt_url,
    )
    result = service.create_expense_request(
        requester_id=current_user.id,
        detail=detail,
    )
    return _to_response(result)


@router.get('/my-requests', response_model=ApprovalListResponse, operation_id='get_my_approval_requests')
async def get_my_requests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[ApprovalStatus] = Query(None),
    current_user: UserModel = Depends(require_employee),
    query_service: ApprovalQueryService = Depends(get_approval_query_service),
) -> ApprovalListResponse:
    """List my submitted approval requests."""
    requests, total = query_service.get_my_requests(
        requester_id=current_user.id,
        page=page,
        size=size,
        status_filter=status,
    )
    return ApprovalListResponse(
        items=[_to_list_item(r) for r in requests],
        total=total,
        page=page,
        size=size,
    )


@router.get('/pending', response_model=ApprovalListResponse, operation_id='get_pending_approvals')
async def get_pending_approvals(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(require_employee),
    query_service: ApprovalQueryService = Depends(get_approval_query_service),
) -> ApprovalListResponse:
    """List approval requests waiting for my approval."""
    requests, total = query_service.get_pending_approvals(
        approver_id=current_user.id,
        page=page,
        size=size,
    )
    return ApprovalListResponse(
        items=[_to_list_item(r) for r in requests],
        total=total,
        page=page,
        size=size,
    )


@router.get('/{request_id}', response_model=ApprovalRequestResponse, operation_id='get_approval_detail')
async def get_request_detail(
    request_id: str,
    current_user: UserModel = Depends(require_employee),
    query_service: ApprovalQueryService = Depends(get_approval_query_service),
) -> ApprovalRequestResponse:
    """Get approval request detail with all steps."""
    result = query_service.get_request_detail(request_id)
    return _to_response(result)


@router.post('/{request_id}/approve', response_model=ApprovalRequestResponse, operation_id='approve_request')
async def approve_request(
    request_id: str,
    request_body: ApproveRejectRequest,
    current_user: UserModel = Depends(require_employee),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Approve the current step of an approval request."""
    result = service.approve(
        request_id=request_id,
        approver_id=current_user.id,
        comment=request_body.comment,
    )
    return _to_response(result)


@router.post('/{request_id}/reject', response_model=ApprovalRequestResponse, operation_id='reject_request')
async def reject_request(
    request_id: str,
    request_body: ApproveRejectRequest,
    current_user: UserModel = Depends(require_employee),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Reject an approval request."""
    result = service.reject(
        request_id=request_id,
        approver_id=current_user.id,
        comment=request_body.comment,
    )
    return _to_response(result)


@router.post('/{request_id}/cancel', response_model=ApprovalRequestResponse, operation_id='cancel_request')
async def cancel_request(
    request_id: str,
    current_user: UserModel = Depends(require_employee),
    service: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Cancel own approval request."""
    result = service.cancel(
        request_id=request_id,
        requester_id=current_user.id,
    )
    return _to_response(result)
