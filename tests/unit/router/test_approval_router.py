"""
Unit tests for ApprovalRouter endpoints.
Tests HTTP layer for approval workflow operations.

測試策略:
- TestClient + dependency_overrides
- 驗證 employee-only 授權
- 驗證 CRUD 端點的正確委派
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, UTC
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.ApprovalRouter import router
from app.router.dependencies.auth import get_current_user
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.domain.ApprovalModel import (
    ApprovalRequest, ApprovalStep, ApprovalType, ApprovalStatus,
    LeaveDetail, LeaveType,
)
from app.exceptions.BaseException import BaseException as AppBaseException


def _create_app():
    app = FastAPI()

    @app.exception_handler(AppBaseException)
    async def handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router)
    return app


def _make_employee():
    return UserModel.reconstitute(
        id="22222222-2222-2222-2222-222222222222", uid="employee", email="emp@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Employee"),
        role=UserRole.EMPLOYEE, email_verified=True,
    )


def _make_approval():
    return ApprovalRequest.create_leave_request(
        requester_id="22222222-2222-2222-2222-222222222222",
        detail=LeaveDetail(
            leave_type=LeaveType.ANNUAL,
            start_date=datetime(2024, 12, 1, tzinfo=UTC),
            end_date=datetime(2024, 12, 5, tzinfo=UTC),
            reason="Holiday",
        ),
        approver_ids=["33333333-3333-3333-3333-333333333333"],
    )


class TestCreateLeaveRequest:
    """測試 POST /approvals/leave 端點"""

    def test_create_leave_success(self):
        """測試員工成功建立請假申請"""
        from app.router.ApprovalRouter import get_approval_service
        app = _create_app()
        employee = _make_employee()
        mock_service = MagicMock()
        mock_service.create_leave_request.return_value = _make_approval()

        app.dependency_overrides[get_current_user] = lambda: employee
        app.dependency_overrides[get_approval_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/approvals/leave", json={
            "leave_type": "ANNUAL",
            "start_date": "2024-12-01T00:00:00Z",
            "end_date": "2024-12-05T00:00:00Z",
            "reason": "Holiday",
        })

        assert response.status_code == 200
        mock_service.create_leave_request.assert_called_once()

    def test_create_leave_unauthenticated(self):
        """測試未認證時回傳 401"""
        app = _create_app()
        client = TestClient(app)
        response = client.post("/approvals/leave", json={
            "leave_type": "ANNUAL",
            "start_date": "2024-12-01T00:00:00Z",
            "end_date": "2024-12-05T00:00:00Z",
            "reason": "Holiday",
        })
        assert response.status_code == 401

    def test_create_leave_normal_user_forbidden(self):
        """測試一般使用者無法建立申請"""
        app = _create_app()
        normal = UserModel.reconstitute(
            id="44444444-4444-4444-4444-444444444444", uid="normal", email="n@example.com",
            hashed_password="h", profile=DomainProfile(name="N"),
            role=UserRole.NORMAL, email_verified=True,
        )
        app.dependency_overrides[get_current_user] = lambda: normal
        client = TestClient(app)

        response = client.post("/approvals/leave", json={
            "leave_type": "ANNUAL",
            "start_date": "2024-12-01T00:00:00Z",
            "end_date": "2024-12-05T00:00:00Z",
            "reason": "Holiday",
        })
        assert response.status_code == 403


class TestGetMyRequests:
    """測試 GET /approvals/my-requests 端點"""

    def test_get_my_requests(self):
        """測試查詢我的申請"""
        from app.router.ApprovalRouter import get_approval_query_service
        app = _create_app()
        employee = _make_employee()
        mock_query = MagicMock()
        mock_query.get_my_requests.return_value = ([], 0)

        app.dependency_overrides[get_current_user] = lambda: employee
        app.dependency_overrides[get_approval_query_service] = lambda: mock_query
        client = TestClient(app)

        response = client.get("/approvals/my-requests?page=1&size=10")
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestApproveReject:
    """測試核准/駁回端點"""

    def test_approve_request(self):
        """測試核准申請"""
        from app.router.ApprovalRouter import get_approval_service
        app = _create_app()
        employee = _make_employee()
        mock_service = MagicMock()
        mock_service.approve.return_value = _make_approval()

        app.dependency_overrides[get_current_user] = lambda: employee
        app.dependency_overrides[get_approval_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/approvals/some-id/approve", json={"comment": "OK"})
        assert response.status_code == 200
        mock_service.approve.assert_called_once()

    def test_reject_request(self):
        """測試駁回申請"""
        from app.router.ApprovalRouter import get_approval_service
        app = _create_app()
        employee = _make_employee()
        mock_service = MagicMock()
        mock_service.reject.return_value = _make_approval()

        app.dependency_overrides[get_current_user] = lambda: employee
        app.dependency_overrides[get_approval_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/approvals/some-id/reject", json={"comment": "Not OK"})
        assert response.status_code == 200
        mock_service.reject.assert_called_once()
