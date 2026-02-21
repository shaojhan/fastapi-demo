"""
Unit tests for ApprovalService and ApprovalQueryService.
Tests the business logic orchestration layer for approval workflows.

測試策略:
- Mock ApprovalUnitOfWork / ApprovalQueryUnitOfWork
- 驗證建立申請、核准、駁回、取消的完整流程
- 驗證異常處理（找不到申請、權限不足、狀態無效）
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC

from app.services.ApprovalService import ApprovalService, ApprovalQueryService
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalType,
    ApprovalStatus,
    LeaveDetail,
    LeaveType,
    ExpenseDetail,
)
from app.exceptions.ApprovalException import (
    ApprovalNotFoundError,
    ApprovalNotAuthorizedError,
    ApprovalInvalidStatusError,
    ApprovalChainError,
)


def _make_leave_detail():
    return LeaveDetail(
        leave_type=LeaveType.ANNUAL,
        start_date=datetime(2024, 12, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 5, tzinfo=UTC),
        reason="Annual leave",
    )


def _make_pending_request(requester_id="req-1", approver_id="appr-1"):
    return ApprovalRequest.create_leave_request(
        requester_id=requester_id,
        detail=_make_leave_detail(),
        approver_ids=[approver_id],
    )


def _setup_uow_mock(mock_uow_class, repo_mock=None, employee_repo_mock=None, session_mock=None):
    mock_uow = MagicMock()
    mock_uow.repo = repo_mock or MagicMock()
    mock_uow.employee_repo = employee_repo_mock or MagicMock()
    mock_uow.session = session_mock or MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow
    return mock_uow


class TestApprovalServiceApprove:
    """測試 ApprovalService.approve 核准功能"""

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_approve_success(self, mock_uow_class):
        """測試成功核准申請"""
        request = _make_pending_request(approver_id="approver-1")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = request
        mock_uow.repo.update.return_value = request

        service = ApprovalService()
        result = service.approve(request.id, "approver-1", comment="OK")

        mock_uow.repo.get_by_id.assert_called_once_with(request.id)
        mock_uow.repo.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_approve_not_found_raises(self, mock_uow_class):
        """測試核准不存在的申請時拋出錯誤"""
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = None

        service = ApprovalService()
        with pytest.raises(ApprovalNotFoundError):
            service.approve("nonexistent-id", "approver-1")

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_approve_wrong_approver_raises(self, mock_uow_class):
        """測試非指定核准人核准時拋出權限錯誤"""
        request = _make_pending_request(approver_id="correct-approver")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = request

        service = ApprovalService()
        with pytest.raises(ApprovalNotAuthorizedError):
            service.approve(request.id, "wrong-approver")


class TestApprovalServiceReject:
    """測試 ApprovalService.reject 駁回功能"""

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_reject_success(self, mock_uow_class):
        """測試成功駁回申請"""
        request = _make_pending_request(approver_id="approver-1")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = request
        mock_uow.repo.update.return_value = request

        service = ApprovalService()
        result = service.reject(request.id, "approver-1", comment="Not approved")

        mock_uow.repo.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_reject_not_found_raises(self, mock_uow_class):
        """測試駁回不存在的申請"""
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = None

        service = ApprovalService()
        with pytest.raises(ApprovalNotFoundError):
            service.reject("nonexistent-id", "approver-1")


class TestApprovalServiceCancel:
    """測試 ApprovalService.cancel 取消功能"""

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_cancel_success(self, mock_uow_class):
        """測試申請人成功取消申請"""
        request = _make_pending_request(requester_id="requester-1")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = request
        mock_uow.repo.update.return_value = request

        service = ApprovalService()
        result = service.cancel(request.id, "requester-1")

        mock_uow.repo.update.assert_called_once()
        mock_uow.commit.assert_called_once()

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_cancel_not_found_raises(self, mock_uow_class):
        """測試取消不存在的申請"""
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = None

        service = ApprovalService()
        with pytest.raises(ApprovalNotFoundError):
            service.cancel("nonexistent-id", "requester-1")

    @patch("app.services.ApprovalService.ApprovalUnitOfWork")
    def test_cancel_by_non_requester_raises(self, mock_uow_class):
        """測試非申請人取消時拋出權限錯誤"""
        request = _make_pending_request(requester_id="requester-1")
        mock_uow = _setup_uow_mock(mock_uow_class)
        mock_uow.repo.get_by_id.return_value = request

        service = ApprovalService()
        with pytest.raises(ApprovalNotAuthorizedError):
            service.cancel(request.id, "someone-else")


class TestApprovalQueryService:
    """測試 ApprovalQueryService 查詢功能"""

    @patch("app.services.ApprovalService.ApprovalQueryUnitOfWork")
    def test_get_my_requests(self, mock_uow_class):
        """測試查詢我的申請"""
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.repo.get_by_requester.return_value = ([], 0)
        mock_uow_class.return_value = mock_uow

        service = ApprovalQueryService()
        results, total = service.get_my_requests("req-1", page=1, size=10)

        assert total == 0
        mock_uow.repo.get_by_requester.assert_called_once_with("req-1", 1, 10, None)

    @patch("app.services.ApprovalService.ApprovalQueryUnitOfWork")
    def test_get_pending_approvals(self, mock_uow_class):
        """測試查詢待核准的申請"""
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.repo.get_pending_by_approver.return_value = ([], 0)
        mock_uow_class.return_value = mock_uow

        service = ApprovalQueryService()
        results, total = service.get_pending_approvals("appr-1", page=1, size=10)

        mock_uow.repo.get_pending_by_approver.assert_called_once_with("appr-1", 1, 10)

    @patch("app.services.ApprovalService.ApprovalQueryUnitOfWork")
    def test_get_request_detail_found(self, mock_uow_class):
        """測試查詢申請詳情"""
        request = _make_pending_request()
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.repo.get_by_id.return_value = request
        mock_uow_class.return_value = mock_uow

        service = ApprovalQueryService()
        result = service.get_request_detail(request.id)
        assert result.id == request.id

    @patch("app.services.ApprovalService.ApprovalQueryUnitOfWork")
    def test_get_request_detail_not_found_raises(self, mock_uow_class):
        """測試查詢不存在的申請詳情"""
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.repo.get_by_id.return_value = None
        mock_uow_class.return_value = mock_uow

        service = ApprovalQueryService()
        with pytest.raises(ApprovalNotFoundError):
            service.get_request_detail("nonexistent-id")
