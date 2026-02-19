import pytest
from datetime import datetime, timedelta, UTC
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalType,
    ApprovalStatus,
    LeaveType,
    LeaveDetail,
    ExpenseDetail,
)


# --- Test Data ---
TEST_REQUESTER_ID = "11d200ac-48d8-4675-bfc0-a3a61af3c499"
TEST_APPROVER_1 = "22d200ac-48d8-4675-bfc0-a3a61af3c499"
TEST_APPROVER_2 = "33d200ac-48d8-4675-bfc0-a3a61af3c499"
TEST_APPROVER_3 = "44d200ac-48d8-4675-bfc0-a3a61af3c499"


def make_leave_detail() -> LeaveDetail:
    return LeaveDetail(
        leave_type=LeaveType.ANNUAL,
        start_date=datetime(2026, 3, 1, 9, 0, 0),
        end_date=datetime(2026, 3, 3, 18, 0, 0),
        reason="家庭旅遊",
    )


def make_expense_detail() -> ExpenseDetail:
    return ExpenseDetail(
        amount=1500.0,
        category="交通費",
        description="出差計程車費",
    )


class TestLeaveDetail:
    """測試 LeaveDetail 值物件"""

    def test_create_valid_leave_detail(self):
        detail = make_leave_detail()
        assert detail.leave_type == LeaveType.ANNUAL
        assert detail.reason == "家庭旅遊"

    def test_leave_detail_invalid_date_range(self):
        with pytest.raises(ValueError, match="Start date must be before end date"):
            LeaveDetail(
                leave_type=LeaveType.SICK,
                start_date=datetime(2026, 3, 3),
                end_date=datetime(2026, 3, 1),
                reason="生病",
            )

    def test_leave_detail_empty_reason(self):
        with pytest.raises(ValueError, match="Reason cannot be empty"):
            LeaveDetail(
                leave_type=LeaveType.PERSONAL,
                start_date=datetime(2026, 3, 1),
                end_date=datetime(2026, 3, 2),
                reason="   ",
            )

    def test_leave_detail_to_dict_and_from_dict(self):
        detail = make_leave_detail()
        d = detail.to_dict()
        restored = LeaveDetail.from_dict(d)
        assert restored.leave_type == detail.leave_type
        assert restored.start_date == detail.start_date
        assert restored.end_date == detail.end_date
        assert restored.reason == detail.reason


class TestExpenseDetail:
    """測試 ExpenseDetail 值物件"""

    def test_create_valid_expense_detail(self):
        detail = make_expense_detail()
        assert detail.amount == 1500.0
        assert detail.category == "交通費"

    def test_expense_detail_zero_amount(self):
        with pytest.raises(ValueError, match="Amount must be positive"):
            ExpenseDetail(amount=0, category="交通費", description="test")

    def test_expense_detail_negative_amount(self):
        with pytest.raises(ValueError, match="Amount must be positive"):
            ExpenseDetail(amount=-100, category="交通費", description="test")

    def test_expense_detail_empty_category(self):
        with pytest.raises(ValueError, match="Category cannot be empty"):
            ExpenseDetail(amount=100, category="", description="test")

    def test_expense_detail_to_dict_and_from_dict(self):
        detail = make_expense_detail()
        d = detail.to_dict()
        restored = ExpenseDetail.from_dict(d)
        assert restored.amount == detail.amount
        assert restored.category == detail.category
        assert restored.description == detail.description


class TestApprovalStep:
    """測試 ApprovalStep 實體"""

    def test_create_step(self):
        step = ApprovalStep(step_order=1, approver_id=TEST_APPROVER_1)
        assert step.status == ApprovalStatus.PENDING
        assert step.comment is None
        assert step.decided_at is None

    def test_approve_step(self):
        step = ApprovalStep(step_order=1, approver_id=TEST_APPROVER_1)
        step.approve("同意")
        assert step.status == ApprovalStatus.APPROVED
        assert step.comment == "同意"
        assert step.decided_at is not None

    def test_reject_step(self):
        step = ApprovalStep(step_order=1, approver_id=TEST_APPROVER_1)
        step.reject("不同意")
        assert step.status == ApprovalStatus.REJECTED
        assert step.comment == "不同意"

    def test_cannot_approve_non_pending_step(self):
        step = ApprovalStep(step_order=1, approver_id=TEST_APPROVER_1)
        step.approve()
        with pytest.raises(ValueError, match="Can only approve a pending step"):
            step.approve()

    def test_cannot_reject_non_pending_step(self):
        step = ApprovalStep(step_order=1, approver_id=TEST_APPROVER_1)
        step.reject()
        with pytest.raises(ValueError, match="Can only reject a pending step"):
            step.reject()


class TestApprovalRequestCreation:
    """測試 ApprovalRequest 建立"""

    def test_create_leave_request(self):
        detail = make_leave_detail()
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=detail,
            approver_ids=[TEST_APPROVER_1, TEST_APPROVER_2],
        )
        assert request.type == ApprovalType.LEAVE
        assert request.status == ApprovalStatus.PENDING
        assert request.requester_id == TEST_REQUESTER_ID
        assert len(request.steps) == 2
        assert request.steps[0].step_order == 1
        assert request.steps[1].step_order == 2

    def test_create_expense_request(self):
        detail = make_expense_detail()
        request = ApprovalRequest.create_expense_request(
            requester_id=TEST_REQUESTER_ID,
            detail=detail,
            approver_ids=[TEST_APPROVER_1],
        )
        assert request.type == ApprovalType.EXPENSE
        assert request.status == ApprovalStatus.PENDING
        assert len(request.steps) == 1

    def test_create_request_without_approvers_raises_error(self):
        detail = make_leave_detail()
        with pytest.raises(ValueError, match="At least one approver"):
            ApprovalRequest.create_leave_request(
                requester_id=TEST_REQUESTER_ID,
                detail=detail,
                approver_ids=[],
            )

    def test_current_step_returns_first_pending(self):
        detail = make_leave_detail()
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=detail,
            approver_ids=[TEST_APPROVER_1, TEST_APPROVER_2],
        )
        current = request.current_step()
        assert current is not None
        assert current.step_order == 1
        assert current.approver_id == TEST_APPROVER_1


class TestApprovalRequestApproval:
    """測試逐級審批流程"""

    def _make_request(self) -> ApprovalRequest:
        return ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1, TEST_APPROVER_2, TEST_APPROVER_3],
        )

    def test_approve_first_step(self):
        request = self._make_request()
        request.approve(TEST_APPROVER_1, "第一關通過")

        assert request.status == ApprovalStatus.PENDING  # still pending
        assert request.steps[0].status == ApprovalStatus.APPROVED
        current = request.current_step()
        assert current.step_order == 2
        assert current.approver_id == TEST_APPROVER_2

    def test_approve_all_steps_completes_request(self):
        request = self._make_request()
        request.approve(TEST_APPROVER_1)
        request.approve(TEST_APPROVER_2)
        request.approve(TEST_APPROVER_3)

        assert request.status == ApprovalStatus.APPROVED
        assert request.is_completed()
        assert request.current_step() is None

    def test_wrong_approver_raises_error(self):
        request = self._make_request()
        with pytest.raises(ValueError, match="not the approver"):
            request.approve(TEST_APPROVER_2)  # should be APPROVER_1

    def test_cannot_approve_non_pending_request(self):
        request = self._make_request()
        request.reject(TEST_APPROVER_1, "駁回")
        with pytest.raises(ValueError, match="Can only approve a pending request"):
            request.approve(TEST_APPROVER_1)


class TestApprovalRequestRejection:
    """測試駁回流程"""

    def test_reject_sets_overall_status(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1, TEST_APPROVER_2],
        )
        request.reject(TEST_APPROVER_1, "理由不充分")

        assert request.status == ApprovalStatus.REJECTED
        assert request.is_completed()
        assert request.steps[0].status == ApprovalStatus.REJECTED
        assert request.steps[0].comment == "理由不充分"
        # Second step remains pending
        assert request.steps[1].status == ApprovalStatus.PENDING

    def test_wrong_approver_cannot_reject(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1, TEST_APPROVER_2],
        )
        with pytest.raises(ValueError, match="not the approver"):
            request.reject(TEST_APPROVER_2)


class TestApprovalRequestCancellation:
    """測試取消流程"""

    def test_requester_can_cancel(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1],
        )
        request.cancel(TEST_REQUESTER_ID)

        assert request.status == ApprovalStatus.CANCELLED
        assert request.is_completed()

    def test_non_requester_cannot_cancel(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1],
        )
        with pytest.raises(ValueError, match="Only the requester"):
            request.cancel(TEST_APPROVER_1)

    def test_cannot_cancel_approved_request(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1],
        )
        request.approve(TEST_APPROVER_1)
        with pytest.raises(ValueError, match="Can only cancel a pending request"):
            request.cancel(TEST_REQUESTER_ID)

    def test_cannot_cancel_rejected_request(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1],
        )
        request.reject(TEST_APPROVER_1)
        with pytest.raises(ValueError, match="Can only cancel a pending request"):
            request.cancel(TEST_REQUESTER_ID)


class TestApprovalRequestReconstitute:
    """測試從持久化重建"""

    def test_reconstitute(self):
        original = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1],
        )

        reconstituted = ApprovalRequest.reconstitute(
            id=original.id,
            type=original.type,
            status=original.status,
            requester_id=original.requester_id,
            detail=original.detail,
            steps=original.steps,
            created_at=original.created_at,
            updated_at=original.updated_at,
        )

        assert reconstituted.id == original.id
        assert reconstituted.type == original.type
        assert reconstituted.status == original.status
        assert len(reconstituted.steps) == len(original.steps)


class TestDetailDict:
    """測試 detail_dict 序列化"""

    def test_leave_detail_dict(self):
        request = ApprovalRequest.create_leave_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_leave_detail(),
            approver_ids=[TEST_APPROVER_1],
        )
        d = request.detail_dict()
        assert d['leave_type'] == 'ANNUAL'
        assert 'start_date' in d
        assert 'reason' in d

    def test_expense_detail_dict(self):
        request = ApprovalRequest.create_expense_request(
            requester_id=TEST_REQUESTER_ID,
            detail=make_expense_detail(),
            approver_ids=[TEST_APPROVER_1],
        )
        d = request.detail_dict()
        assert d['amount'] == 1500.0
        assert d['category'] == '交通費'
