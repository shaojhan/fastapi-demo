from __future__ import annotations

from typing import List, Tuple

from loguru import logger

from app.services.unitofwork.ApprovalUnitOfWork import (
    ApprovalUnitOfWork,
    ApprovalQueryUnitOfWork,
)
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalType,
    ApprovalStatus,
    LeaveDetail,
    ExpenseDetail,
)
from app.domain.EmployeeModel import Department, EmployeeModel
from app.domain.UserModel import UserRole
from app.exceptions.ApprovalException import (
    ApprovalNotFoundError,
    ApprovalNotAuthorizedError,
    ApprovalInvalidStatusError,
    ApprovalChainError,
)

from database.models.user import User
from uuid import UUID


class ApprovalService:
    """Application service for approval request write operations."""

    def _build_approval_chain(
        self,
        approval_type: ApprovalType,
        requester_user_id: str,
        uow: ApprovalUnitOfWork,
    ) -> list[str]:
        """
        Build the approval chain based on department hierarchy.

        For LEAVE: department managers (by role level) → ADMIN
        For EXPENSE: department managers (by role level) → HR representative → ADMIN

        Returns:
            Ordered list of approver user_ids.
        """
        # Find the requester's employee record
        employees = uow.employee_repo.get_all()
        requester_employee = None
        for emp in employees:
            if emp.user_id == requester_user_id:
                requester_employee = emp
                break

        if not requester_employee:
            raise ApprovalChainError(message="Requester is not registered as an employee.")

        requester_level = requester_employee.role.level if requester_employee.role else 0
        department = requester_employee.department

        approver_ids: list[str] = []

        # Find department colleagues with higher role level
        dept_employees = uow.employee_repo.get_by_department(department)
        higher_level_employees = [
            emp for emp in dept_employees
            if emp.user_id
            and emp.user_id != requester_user_id
            and emp.role
            and emp.role.level > requester_level
        ]
        # Sort by level ascending (lowest superior first → highest last)
        higher_level_employees.sort(key=lambda e: e.role.level)

        for emp in higher_level_employees:
            approver_ids.append(emp.user_id)

        # For EXPENSE: add HR department representative
        if approval_type == ApprovalType.EXPENSE and department != Department.HR:
            hr_employees = uow.employee_repo.get_by_department(Department.HR)
            # Pick the highest-level HR employee
            hr_with_roles = [
                emp for emp in hr_employees
                if emp.user_id and emp.role
            ]
            hr_with_roles.sort(key=lambda e: e.role.level, reverse=True)
            if hr_with_roles:
                hr_approver_id = hr_with_roles[0].user_id
                if hr_approver_id not in approver_ids:
                    approver_ids.append(hr_approver_id)

        # Final approver: find an ADMIN user
        admin_user = uow.session.query(User).filter(
            User.role == UserRole.ADMIN.value
        ).first()
        if admin_user:
            admin_id = str(admin_user.id)
            if admin_id not in approver_ids:
                approver_ids.append(admin_id)

        if not approver_ids:
            raise ApprovalChainError()

        logger.info(
            f"Built approval chain for {approval_type.value} request: "
            f"requester={requester_user_id}, chain={approver_ids}"
        )

        return approver_ids

    def create_leave_request(
        self,
        requester_id: str,
        detail: LeaveDetail,
    ) -> ApprovalRequest:
        with ApprovalUnitOfWork() as uow:
            approver_ids = self._build_approval_chain(
                ApprovalType.LEAVE, requester_id, uow
            )
            request = ApprovalRequest.create_leave_request(
                requester_id=requester_id,
                detail=detail,
                approver_ids=approver_ids,
            )
            created = uow.repo.add(request)
            uow.commit()
            logger.info(f"Leave request created: id={created.id}, requester={requester_id}")
            return created

    def create_expense_request(
        self,
        requester_id: str,
        detail: ExpenseDetail,
    ) -> ApprovalRequest:
        with ApprovalUnitOfWork() as uow:
            approver_ids = self._build_approval_chain(
                ApprovalType.EXPENSE, requester_id, uow
            )
            request = ApprovalRequest.create_expense_request(
                requester_id=requester_id,
                detail=detail,
                approver_ids=approver_ids,
            )
            created = uow.repo.add(request)
            uow.commit()
            logger.info(f"Expense request created: id={created.id}, requester={requester_id}")
            return created

    def approve(
        self,
        request_id: str,
        approver_id: str,
        comment: str | None = None,
    ) -> ApprovalRequest:
        with ApprovalUnitOfWork() as uow:
            request = uow.repo.get_by_id(request_id)
            if not request:
                raise ApprovalNotFoundError()

            try:
                request.approve(approver_id, comment)
            except ValueError as e:
                if "not the approver" in str(e):
                    raise ApprovalNotAuthorizedError(message=str(e))
                raise ApprovalInvalidStatusError(message=str(e))

            updated = uow.repo.update(request)
            uow.commit()
            logger.info(
                f"Approval request {request_id} approved by {approver_id}, "
                f"new status: {updated.status.value}"
            )
            return updated

    def reject(
        self,
        request_id: str,
        approver_id: str,
        comment: str | None = None,
    ) -> ApprovalRequest:
        with ApprovalUnitOfWork() as uow:
            request = uow.repo.get_by_id(request_id)
            if not request:
                raise ApprovalNotFoundError()

            try:
                request.reject(approver_id, comment)
            except ValueError as e:
                if "not the approver" in str(e):
                    raise ApprovalNotAuthorizedError(message=str(e))
                raise ApprovalInvalidStatusError(message=str(e))

            updated = uow.repo.update(request)
            uow.commit()
            logger.info(f"Approval request {request_id} rejected by {approver_id}")
            return updated

    def cancel(
        self,
        request_id: str,
        requester_id: str,
    ) -> ApprovalRequest:
        with ApprovalUnitOfWork() as uow:
            request = uow.repo.get_by_id(request_id)
            if not request:
                raise ApprovalNotFoundError()

            try:
                request.cancel(requester_id)
            except ValueError as e:
                if "Only the requester" in str(e):
                    raise ApprovalNotAuthorizedError(message=str(e))
                raise ApprovalInvalidStatusError(message=str(e))

            updated = uow.repo.update(request)
            uow.commit()
            logger.info(f"Approval request {request_id} cancelled by {requester_id}")
            return updated


class ApprovalQueryService:
    """Application service for approval read operations."""

    def get_my_requests(
        self,
        requester_id: str,
        page: int,
        size: int,
        status_filter: ApprovalStatus | None = None,
    ) -> Tuple[List[ApprovalRequest], int]:
        with ApprovalQueryUnitOfWork() as uow:
            return uow.repo.get_by_requester(requester_id, page, size, status_filter)

    def get_pending_approvals(
        self,
        approver_id: str,
        page: int,
        size: int,
    ) -> Tuple[List[ApprovalRequest], int]:
        with ApprovalQueryUnitOfWork() as uow:
            return uow.repo.get_pending_by_approver(approver_id, page, size)

    def get_request_detail(self, request_id: str) -> ApprovalRequest:
        with ApprovalQueryUnitOfWork() as uow:
            result = uow.repo.get_by_id(request_id)
            if not result:
                raise ApprovalNotFoundError()
            return result
