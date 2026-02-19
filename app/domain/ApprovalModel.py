from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import uuid4


class ApprovalType(str, Enum):
    LEAVE = 'LEAVE'
    EXPENSE = 'EXPENSE'


class ApprovalStatus(str, Enum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'


class LeaveType(str, Enum):
    ANNUAL = 'ANNUAL'
    SICK = 'SICK'
    PERSONAL = 'PERSONAL'
    OTHER = 'OTHER'


@dataclass(frozen=True)
class LeaveDetail:
    leave_type: LeaveType
    start_date: datetime
    end_date: datetime
    reason: str

    def __post_init__(self):
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        if not self.reason or not self.reason.strip():
            raise ValueError("Reason cannot be empty")

    def to_dict(self) -> dict:
        return {
            'leave_type': self.leave_type.value,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'reason': self.reason,
        }

    @staticmethod
    def from_dict(data: dict) -> "LeaveDetail":
        return LeaveDetail(
            leave_type=LeaveType(data['leave_type']),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            reason=data['reason'],
        )


@dataclass(frozen=True)
class ExpenseDetail:
    amount: float
    category: str
    description: str
    receipt_url: str | None = None

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if not self.category or not self.category.strip():
            raise ValueError("Category cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Description cannot be empty")

    def to_dict(self) -> dict:
        return {
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'receipt_url': self.receipt_url,
        }

    @staticmethod
    def from_dict(data: dict) -> "ExpenseDetail":
        return ExpenseDetail(
            amount=data['amount'],
            category=data['category'],
            description=data['description'],
            receipt_url=data.get('receipt_url'),
        )


@dataclass
class ApprovalStep:
    step_order: int
    approver_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    comment: str | None = None
    decided_at: datetime | None = None
    id: int | None = None
    created_at: datetime | None = None

    def approve(self, comment: str | None = None) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError("Can only approve a pending step")
        self.status = ApprovalStatus.APPROVED
        self.comment = comment
        self.decided_at = datetime.now(UTC)

    def reject(self, comment: str | None = None) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError("Can only reject a pending step")
        self.status = ApprovalStatus.REJECTED
        self.comment = comment
        self.decided_at = datetime.now(UTC)


class ApprovalRequest:
    """
    Aggregate Root representing an approval request.
    Use factory methods `create_leave_request`, `create_expense_request`, or `reconstitute` to create instances.
    """

    def __init__(
        self,
        id: str,
        type: ApprovalType,
        status: ApprovalStatus,
        requester_id: str,
        detail: LeaveDetail | ExpenseDetail,
        steps: list[ApprovalStep],
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self._id = id
        self._type = type
        self._status = status
        self._requester_id = requester_id
        self._detail = detail
        self._steps = sorted(steps, key=lambda s: s.step_order)
        self._created_at = created_at
        self._updated_at = updated_at

    # Properties
    @property
    def id(self) -> str:
        return self._id

    @property
    def type(self) -> ApprovalType:
        return self._type

    @property
    def status(self) -> ApprovalStatus:
        return self._status

    @property
    def requester_id(self) -> str:
        return self._requester_id

    @property
    def detail(self) -> LeaveDetail | ExpenseDetail:
        return self._detail

    @property
    def steps(self) -> list[ApprovalStep]:
        return list(self._steps)

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    # Factory methods
    @staticmethod
    def create_leave_request(
        requester_id: str,
        detail: LeaveDetail,
        approver_ids: list[str],
    ) -> "ApprovalRequest":
        if not approver_ids:
            raise ValueError("At least one approver is required")

        steps = [
            ApprovalStep(
                step_order=i + 1,
                approver_id=approver_id,
                created_at=datetime.now(UTC),
            )
            for i, approver_id in enumerate(approver_ids)
        ]

        return ApprovalRequest(
            id=str(uuid4()),
            type=ApprovalType.LEAVE,
            status=ApprovalStatus.PENDING,
            requester_id=requester_id,
            detail=detail,
            steps=steps,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def create_expense_request(
        requester_id: str,
        detail: ExpenseDetail,
        approver_ids: list[str],
    ) -> "ApprovalRequest":
        if not approver_ids:
            raise ValueError("At least one approver is required")

        steps = [
            ApprovalStep(
                step_order=i + 1,
                approver_id=approver_id,
                created_at=datetime.now(UTC),
            )
            for i, approver_id in enumerate(approver_ids)
        ]

        return ApprovalRequest(
            id=str(uuid4()),
            type=ApprovalType.EXPENSE,
            status=ApprovalStatus.PENDING,
            requester_id=requester_id,
            detail=detail,
            steps=steps,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def reconstitute(
        id: str,
        type: ApprovalType,
        status: ApprovalStatus,
        requester_id: str,
        detail: LeaveDetail | ExpenseDetail,
        steps: list[ApprovalStep],
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "ApprovalRequest":
        return ApprovalRequest(
            id=id,
            type=type,
            status=status,
            requester_id=requester_id,
            detail=detail,
            steps=steps,
            created_at=created_at,
            updated_at=updated_at,
        )

    # Business methods
    def current_step(self) -> ApprovalStep | None:
        for step in self._steps:
            if step.status == ApprovalStatus.PENDING:
                return step
        return None

    def approve(self, approver_id: str, comment: str | None = None) -> None:
        if self._status != ApprovalStatus.PENDING:
            raise ValueError("Can only approve a pending request")

        step = self.current_step()
        if step is None:
            raise ValueError("No pending step to approve")

        if step.approver_id != approver_id:
            raise ValueError("You are not the approver for the current step")

        step.approve(comment)
        self._updated_at = datetime.now(UTC)

        # Check if all steps are approved
        if all(s.status == ApprovalStatus.APPROVED for s in self._steps):
            self._status = ApprovalStatus.APPROVED

    def reject(self, approver_id: str, comment: str | None = None) -> None:
        if self._status != ApprovalStatus.PENDING:
            raise ValueError("Can only reject a pending request")

        step = self.current_step()
        if step is None:
            raise ValueError("No pending step to reject")

        if step.approver_id != approver_id:
            raise ValueError("You are not the approver for the current step")

        step.reject(comment)
        self._status = ApprovalStatus.REJECTED
        self._updated_at = datetime.now(UTC)

    def cancel(self, requester_id: str) -> None:
        if self._requester_id != requester_id:
            raise ValueError("Only the requester can cancel this request")

        if self._status != ApprovalStatus.PENDING:
            raise ValueError("Can only cancel a pending request")

        self._status = ApprovalStatus.CANCELLED
        self._updated_at = datetime.now(UTC)

    def is_completed(self) -> bool:
        return self._status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
        )

    def detail_dict(self) -> dict:
        return self._detail.to_dict()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApprovalRequest):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
