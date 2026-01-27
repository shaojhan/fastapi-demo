from fastapi import APIRouter, Depends

from app.router.schemas.EmployeeSchema import (
    AssignEmployeeRequest,
    AssignEmployeeResponse,
    RoleInfoResponse,
)
from app.services.EmployeeService import EmployeeService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_admin


router = APIRouter(prefix='/employees', tags=['employee'])


def get_employee_service() -> EmployeeService:
    return EmployeeService()


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
