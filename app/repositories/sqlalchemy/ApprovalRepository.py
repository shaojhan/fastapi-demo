from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import object_session

from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStep,
    ApprovalType,
    ExpenseDetail,
    LeaveDetail,
)
from database.models.approval import ApprovalRequestORM, ApprovalStepORM
from database.models.employee import Employee
from database.models.user import Profile

from .BaseRepository import BaseRepository


def _approval_step_to_domain(step: ApprovalStepORM) -> ApprovalStep:
    approver = step.approver
    employee = approver.employee if approver else None
    role = employee.role if employee else None
    profile = approver.profile if approver else None
    session = object_session(step)

    if session and not profile:
        profile = session.query(Profile).filter(Profile.user_id == step.approver_id).first()

    if session and not employee:
        employee = session.query(Employee).filter(Employee.user_id == step.approver_id).first()
        role = employee.role if employee else None

    return ApprovalStep(
        id=step.id,
        step_order=step.step_order,
        approver_id=str(step.approver_id),
        approver_name=profile.name if profile else None,
        approver_department=employee.department if employee else None,
        approver_role_name=role.name if role else None,
        approver_role_level=role.level if role else None,
        status=ApprovalStatus(step.status),
        comment=step.comment,
        decided_at=step.decided_at,
        created_at=step.created_at,
    )


class ApprovalRepository(BaseRepository):
    """Repository for ApprovalRequest aggregate persistence operations."""

    def add(self, approval: ApprovalRequest) -> ApprovalRequest:
        entity = ApprovalRequestORM(
            id=UUID(approval.id),
            type=approval.type.value,
            status=approval.status.value,
            requester_id=UUID(approval.requester_id),
            detail_json=approval.detail_dict(),
        )

        for step in approval.steps:
            step_entity = ApprovalStepORM(
                step_order=step.step_order,
                approver_id=UUID(step.approver_id),
                status=step.status.value,
            )
            entity.steps.append(step_entity)

        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)

        return self._to_domain_model(entity)

    def get_by_id(self, request_id: str) -> ApprovalRequest | None:
        entity = self.db.query(ApprovalRequestORM).filter(
            ApprovalRequestORM.id == UUID(request_id)
        ).first()

        if not entity:
            return None

        return self._to_domain_model(entity)

    def update(self, approval: ApprovalRequest) -> ApprovalRequest:
        entity = self.db.query(ApprovalRequestORM).filter(
            ApprovalRequestORM.id == UUID(approval.id)
        ).first()

        if not entity:
            raise ValueError(f"ApprovalRequest with ID {approval.id} not found")

        entity.status = approval.status.value
        entity.updated_at = approval.updated_at

        # Update each step
        domain_steps = {s.step_order: s for s in approval.steps}
        for step_entity in entity.steps:
            domain_step = domain_steps.get(step_entity.step_order)
            if domain_step:
                step_entity.status = domain_step.status.value
                step_entity.comment = domain_step.comment
                step_entity.decided_at = domain_step.decided_at

        self.db.flush()
        self.db.refresh(entity)

        return self._to_domain_model(entity)

    def _to_domain_model(self, entity: ApprovalRequestORM) -> ApprovalRequest:
        approval_type = ApprovalType(entity.type)

        detail: LeaveDetail | ExpenseDetail
        if approval_type == ApprovalType.LEAVE:
            detail = LeaveDetail.from_dict(entity.detail_json)
        else:
            detail = ExpenseDetail.from_dict(entity.detail_json)

        steps = [_approval_step_to_domain(step) for step in entity.steps]

        return ApprovalRequest.reconstitute(
            id=str(entity.id),
            type=approval_type,
            status=ApprovalStatus(entity.status),
            requester_id=str(entity.requester_id),
            detail=detail,
            steps=steps,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class ApprovalQueryRepository(BaseRepository):
    """Repository for read-only approval queries."""

    def get_by_id(self, request_id: str) -> ApprovalRequest | None:
        entity = self.db.query(ApprovalRequestORM).filter(
            ApprovalRequestORM.id == UUID(request_id)
        ).first()

        if not entity:
            return None

        return self._to_domain_model(entity)

    def get_pending_by_approver(
        self, approver_id: str, page: int, size: int
    ) -> tuple[list[ApprovalRequest], int]:
        """Get approval requests where the user is the current pending approver.

        The "current step" is the lowest-order PENDING step of a request (see
        ``ApprovalRequest.current_step``). We push that rule entirely into SQL so
        pagination and the total count stay consistent — the previous version
        paginated first and filtered in Python, which produced wrong totals and
        short pages.
        """
        # Lowest pending step_order per request.
        min_pending_order = (
            self.db.query(
                ApprovalStepORM.approval_request_id.label("request_id"),
                func.min(ApprovalStepORM.step_order).label("min_order"),
            )
            .filter(ApprovalStepORM.status == ApprovalStatus.PENDING.value)
            .group_by(ApprovalStepORM.approval_request_id)
            .subquery()
        )

        # Requests whose current (lowest-order) pending step belongs to this approver.
        current_for_approver = (
            self.db.query(ApprovalStepORM.approval_request_id)
            .join(
                min_pending_order,
                (ApprovalStepORM.approval_request_id == min_pending_order.c.request_id)
                & (ApprovalStepORM.step_order == min_pending_order.c.min_order),
            )
            .filter(
                ApprovalStepORM.status == ApprovalStatus.PENDING.value,
                ApprovalStepORM.approver_id == UUID(approver_id),
            )
            .subquery()
        )

        query = self.db.query(ApprovalRequestORM).filter(
            ApprovalRequestORM.status == ApprovalStatus.PENDING.value,
            ApprovalRequestORM.id.in_(
                self.db.query(current_for_approver.c.approval_request_id)
            ),
        )

        total = query.count()
        entities = (
            query.order_by(ApprovalRequestORM.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        return [self._to_domain_model(e) for e in entities], total

    def get_by_requester(
        self,
        requester_id: str,
        page: int,
        size: int,
        status_filter: ApprovalStatus | None = None,
    ) -> tuple[list[ApprovalRequest], int]:
        query = self.db.query(ApprovalRequestORM).filter(
            ApprovalRequestORM.requester_id == UUID(requester_id)
        )

        if status_filter:
            query = query.filter(ApprovalRequestORM.status == status_filter.value)

        total = query.count()
        entities = (
            query.order_by(ApprovalRequestORM.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        return [self._to_domain_model(e) for e in entities], total

    def _to_domain_model(self, entity: ApprovalRequestORM) -> ApprovalRequest:
        approval_type = ApprovalType(entity.type)

        detail: LeaveDetail | ExpenseDetail
        if approval_type == ApprovalType.LEAVE:
            detail = LeaveDetail.from_dict(entity.detail_json)
        else:
            detail = ExpenseDetail.from_dict(entity.detail_json)

        steps = [_approval_step_to_domain(step) for step in entity.steps]

        return ApprovalRequest.reconstitute(
            id=str(entity.id),
            type=approval_type,
            status=ApprovalStatus(entity.status),
            requester_id=str(entity.requester_id),
            detail=detail,
            steps=steps,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
