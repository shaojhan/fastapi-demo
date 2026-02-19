from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import and_

from .BaseRepository import BaseRepository
from database.models.approval import ApprovalRequestORM, ApprovalStepORM
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalType,
    ApprovalStatus,
    LeaveDetail,
    ExpenseDetail,
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

    def get_by_id(self, request_id: str) -> Optional[ApprovalRequest]:
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

        if approval_type == ApprovalType.LEAVE:
            detail = LeaveDetail.from_dict(entity.detail_json)
        else:
            detail = ExpenseDetail.from_dict(entity.detail_json)

        steps = [
            ApprovalStep(
                id=step.id,
                step_order=step.step_order,
                approver_id=str(step.approver_id),
                status=ApprovalStatus(step.status),
                comment=step.comment,
                decided_at=step.decided_at,
                created_at=step.created_at,
            )
            for step in entity.steps
        ]

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

    def get_by_id(self, request_id: str) -> Optional[ApprovalRequest]:
        entity = self.db.query(ApprovalRequestORM).filter(
            ApprovalRequestORM.id == UUID(request_id)
        ).first()

        if not entity:
            return None

        return self._to_domain_model(entity)

    def get_pending_by_approver(
        self, approver_id: str, page: int, size: int
    ) -> Tuple[List[ApprovalRequest], int]:
        """Get approval requests where the user is the current pending approver."""
        # Subquery: find request IDs where this user has a pending step
        # and the step is the lowest-order pending step (i.e., the current step)
        from sqlalchemy import func as sqlfunc

        # Find requests where this approver has a PENDING step
        # and no earlier step is also PENDING (meaning it's their turn)
        pending_step_requests = (
            self.db.query(ApprovalStepORM.approval_request_id)
            .filter(
                ApprovalStepORM.approver_id == UUID(approver_id),
                ApprovalStepORM.status == ApprovalStatus.PENDING.value,
            )
            .subquery()
        )

        query = (
            self.db.query(ApprovalRequestORM)
            .filter(
                ApprovalRequestORM.id.in_(
                    self.db.query(pending_step_requests.c.approval_request_id)
                ),
                ApprovalRequestORM.status == ApprovalStatus.PENDING.value,
            )
        )

        total = query.count()
        entities = (
            query.order_by(ApprovalRequestORM.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        # Filter to only include requests where this approver is actually the current step
        results = []
        for entity in entities:
            domain = self._to_domain_model(entity)
            current = domain.current_step()
            if current and current.approver_id == approver_id:
                results.append(domain)

        return results, len(results)

    def get_by_requester(
        self,
        requester_id: str,
        page: int,
        size: int,
        status_filter: ApprovalStatus | None = None,
    ) -> Tuple[List[ApprovalRequest], int]:
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

        if approval_type == ApprovalType.LEAVE:
            detail = LeaveDetail.from_dict(entity.detail_json)
        else:
            detail = ExpenseDetail.from_dict(entity.detail_json)

        steps = [
            ApprovalStep(
                id=step.id,
                step_order=step.step_order,
                approver_id=str(step.approver_id),
                status=ApprovalStatus(step.status),
                comment=step.comment,
                decided_at=step.decided_at,
                created_at=step.created_at,
            )
            for step in entity.steps
        ]

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
