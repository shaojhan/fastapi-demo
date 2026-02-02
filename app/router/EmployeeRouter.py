from fastapi import APIRouter, Depends, Query

from app.router.schemas.EmployeeSchema import (
    AssignEmployeeRequest,
    AssignEmployeeResponse,
    RoleInfoResponse,
    EmployeeListItem,
    EmployeeListResponse,
)
from app.services.EmployeeService import EmployeeService, EmployeeQueryService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_admin


router = APIRouter(prefix='/employees', tags=['employee'])


def get_employee_service() -> EmployeeService:
    return EmployeeService()


def get_employee_query_service() -> EmployeeQueryService:
    return EmployeeQueryService()


@router.get('/', response_model=EmployeeListResponse, operation_id='list_employees')
async def list_employees(
    page: int = Query(1, ge=1, description='頁碼'),
    size: int = Query(20, ge=1, le=100, description='每頁筆數'),
    admin_user: UserModel = Depends(require_admin),
    query_service: EmployeeQueryService = Depends(get_employee_query_service),
) -> EmployeeListResponse:
    """List all employees with pagination (Admin only)."""
    employees, total = query_service.get_all_employees_paginated(page, size)
    items = [
        EmployeeListItem(
            id=emp.id,
            idno=emp.idno,
            department=emp.department,
            user_id=emp.user_id,
            role=RoleInfoResponse(
                id=emp.role.id,
                name=emp.role.name,
                level=emp.role.level,
                authorities=emp.role.authorities,
            ) if emp.role else None,
            created_at=emp.created_at,
        )
        for emp in employees
    ]
    return EmployeeListResponse(items=items, total=total, page=page, size=size)


@router.post(
    '/assign',
    response_model=AssignEmployeeResponse,
    operation_id='assign_user_as_employee',
    summary='Assign a user as an employee (Admin only)',
)
async def assign_user_as_employee(
    request_body: AssignEmployeeRequest,
    admin_user: UserModel = Depends(require_admin),
    employee_service: EmployeeService = Depends(get_employee_service),
) -> AssignEmployeeResponse:
    """
    Assign an existing user as an employee.
    Only administrators can perform this action.
    """
    employee = employee_service.assign_user_as_employee(
        user_id=str(request_body.user_id),
        idno=request_body.idno,
        department=request_body.department,
        role_id=request_body.role_id,
    )

    role_response = None
    if employee.role:
        role_response = RoleInfoResponse(
            id=employee.role.id,
            name=employee.role.name,
            level=employee.role.level,
            authorities=employee.role.authorities,
        )

    return AssignEmployeeResponse(
        id=employee.id,
        idno=employee.idno,
        department=employee.department,
        user_id=employee.user_id,
        role=role_response,
        created_at=employee.created_at,
    )
