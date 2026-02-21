"""
Unit tests for ApprovalRepository and ApprovalQueryRepository.
Tests the data access layer for Approval aggregate persistence.

測試策略:
- 使用 SQLite in-memory 資料庫進行真實 ORM 操作
- 驗證 ApprovalRequest + ApprovalStep 的完整 CRUD
- 測試分頁查詢和狀態過濾功能
"""
import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.ApprovalRepository import (
    ApprovalRepository,
    ApprovalQueryRepository,
)
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalType,
    ApprovalStatus,
    LeaveDetail,
    LeaveType,
    ExpenseDetail,
)


def _make_leave_detail():
    return LeaveDetail(
        leave_type=LeaveType.ANNUAL,
        start_date=datetime(2024, 12, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 5, tzinfo=UTC),
        reason="Annual leave",
    )


def _make_expense_detail():
    return ExpenseDetail(
        amount=1500.0,
        category="Travel",
        description="Business trip expenses",
    )


class TestApprovalRepository:
    """測試 ApprovalRepository 的寫入操作"""

    def test_add_leave_request(self, test_db_session: Session, sample_users):
        """測試新增請假申請"""
        repo = ApprovalRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_id = str(sample_users[2].id)

        request = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=[approver_id],
        )

        result = repo.add(request)
        test_db_session.commit()

        assert result.id is not None
        assert result.type == ApprovalType.LEAVE
        assert result.status == ApprovalStatus.PENDING
        assert result.requester_id == requester_id
        assert len(result.steps) == 1
        assert result.steps[0].approver_id == approver_id

    def test_add_expense_request(self, test_db_session: Session, sample_users):
        """測試新增費用申請"""
        repo = ApprovalRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_id = str(sample_users[2].id)

        request = ApprovalRequest.create_expense_request(
            requester_id=requester_id,
            detail=_make_expense_detail(),
            approver_ids=[approver_id],
        )

        result = repo.add(request)
        test_db_session.commit()

        assert result.type == ApprovalType.EXPENSE
        assert isinstance(result.detail, ExpenseDetail)
        assert result.detail.amount == 1500.0

    def test_add_request_with_multiple_steps(self, test_db_session: Session, sample_users):
        """測試新增多步驟簽核流程"""
        repo = ApprovalRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_ids = [str(sample_users[1].id), str(sample_users[2].id)]

        request = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=approver_ids,
        )

        result = repo.add(request)
        test_db_session.commit()

        assert len(result.steps) == 2
        assert result.steps[0].step_order == 1
        assert result.steps[1].step_order == 2

    def test_get_by_id_existing(self, test_db_session: Session, sample_users):
        """測試以 ID 查詢存在的申請"""
        repo = ApprovalRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_id = str(sample_users[2].id)

        request = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=[approver_id],
        )
        created = repo.add(request)
        test_db_session.commit()

        result = repo.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.type == ApprovalType.LEAVE

    def test_get_by_id_non_existing(self, test_db_session: Session):
        """測試以 ID 查詢不存在的申請"""
        repo = ApprovalRepository(test_db_session)
        result = repo.get_by_id(str(uuid4()))
        assert result is None

    def test_update_status(self, test_db_session: Session, sample_users):
        """測試更新申請狀態"""
        repo = ApprovalRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_id = str(sample_users[2].id)

        request = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=[approver_id],
        )
        created = repo.add(request)
        test_db_session.commit()

        # Approve the request
        created.approve(approver_id=approver_id, comment="Approved!")
        updated = repo.update(created)
        test_db_session.commit()

        assert updated.status == ApprovalStatus.APPROVED
        assert updated.steps[0].status == ApprovalStatus.APPROVED
        assert updated.steps[0].comment == "Approved!"


class TestApprovalQueryRepository:
    """測試 ApprovalQueryRepository 的查詢方法"""

    def test_get_by_id(self, test_db_session: Session, sample_users):
        """測試查詢單一申請"""
        write_repo = ApprovalRepository(test_db_session)
        query_repo = ApprovalQueryRepository(test_db_session)

        request = ApprovalRequest.create_leave_request(
            requester_id=str(sample_users[0].id),
            detail=_make_leave_detail(),
            approver_ids=[str(sample_users[2].id)],
        )
        created = write_repo.add(request)
        test_db_session.commit()

        result = query_repo.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    def test_get_by_requester(self, test_db_session: Session, sample_users):
        """測試依申請人查詢"""
        write_repo = ApprovalRepository(test_db_session)
        query_repo = ApprovalQueryRepository(test_db_session)
        requester_id = str(sample_users[0].id)

        for _ in range(3):
            request = ApprovalRequest.create_leave_request(
                requester_id=requester_id,
                detail=_make_leave_detail(),
                approver_ids=[str(sample_users[2].id)],
            )
            write_repo.add(request)
        test_db_session.commit()

        results, total = query_repo.get_by_requester(requester_id, page=1, size=10)

        assert total == 3
        assert len(results) == 3
        assert all(r.requester_id == requester_id for r in results)

    def test_get_by_requester_with_status_filter(self, test_db_session: Session, sample_users):
        """測試依狀態過濾查詢"""
        write_repo = ApprovalRepository(test_db_session)
        query_repo = ApprovalQueryRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_id = str(sample_users[2].id)

        # Create 2 requests, approve 1
        req1 = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=[approver_id],
        )
        req2 = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=[approver_id],
        )
        created1 = write_repo.add(req1)
        write_repo.add(req2)
        test_db_session.commit()

        created1.approve(approver_id, "OK")
        write_repo.update(created1)
        test_db_session.commit()

        pending, pending_total = query_repo.get_by_requester(
            requester_id, page=1, size=10, status_filter=ApprovalStatus.PENDING
        )
        assert pending_total == 1

    def test_get_by_requester_pagination(self, test_db_session: Session, sample_users):
        """測試分頁查詢"""
        write_repo = ApprovalRepository(test_db_session)
        query_repo = ApprovalQueryRepository(test_db_session)
        requester_id = str(sample_users[0].id)

        for _ in range(5):
            request = ApprovalRequest.create_leave_request(
                requester_id=requester_id,
                detail=_make_leave_detail(),
                approver_ids=[str(sample_users[2].id)],
            )
            write_repo.add(request)
        test_db_session.commit()

        page1, total = query_repo.get_by_requester(requester_id, page=1, size=2)
        assert total == 5
        assert len(page1) == 2

    def test_get_pending_by_approver(self, test_db_session: Session, sample_users):
        """測試查詢待簽核的申請"""
        write_repo = ApprovalRepository(test_db_session)
        query_repo = ApprovalQueryRepository(test_db_session)
        requester_id = str(sample_users[0].id)
        approver_id = str(sample_users[2].id)

        request = ApprovalRequest.create_leave_request(
            requester_id=requester_id,
            detail=_make_leave_detail(),
            approver_ids=[approver_id],
        )
        write_repo.add(request)
        test_db_session.commit()

        results, total = query_repo.get_pending_by_approver(approver_id, page=1, size=10)

        assert total >= 1
        assert all(r.status == ApprovalStatus.PENDING for r in results)
