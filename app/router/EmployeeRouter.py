from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from loguru import logger

from app.router.schemas.EmployeeSchema import (
    AssignEmployeeRequest,
    AssignEmployeeResponse,
    RoleInfoResponse,
    EmployeeListItem,
    EmployeeListResponse,
    CsvUploadResultItem,
    CsvUploadResponse,
)
from app.services.EmployeeService import EmployeeService, EmployeeQueryService
from app.services.EmailService import EmailService
from app.services.FileReadService import FileReadService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import require_admin


router = APIRouter(prefix='/employees', tags=['employee'])


def get_employee_service() -> EmployeeService:
    return EmployeeService()


def get_employee_query_service() -> EmployeeQueryService:
    return EmployeeQueryService()


def get_file_read_service() -> FileReadService:
    return FileReadService()


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


REQUIRED_CSV_HEADERS = {'idno', 'department', 'email', 'uid', 'role_id'}


@router.post(
    '/upload-csv',
    response_model=CsvUploadResponse,
    operation_id='upload_employees_csv',
    summary='Batch create employees from CSV file (Admin only)',
)
async def upload_employees_csv(
    file: UploadFile = File(..., description='CSV 檔案 (欄位: idno, department, email, uid, role_id)'),
    admin_user: UserModel = Depends(require_admin),
    employee_service: EmployeeService = Depends(get_employee_service),
    file_read_service: FileReadService = Depends(get_file_read_service),
) -> CsvUploadResponse:
    """
    Upload a CSV file to batch-create employee accounts.
    If an employee's email/uid doesn't match an existing user,
    a new user account is automatically created with a random password.
    Only administrators can perform this action.
    """
    # Read and validate CSV via FileReadService
    try:
        rows = await file_read_service.read_csv(file, REQUIRED_CSV_HEADERS)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process batch import
    import_result = employee_service.batch_import_employees(rows)

    # Send password emails for newly created users (best-effort)
    if import_result.new_user_credentials:
        email_service = EmailService()
        for email, uid, password in import_result.new_user_credentials:
            try:
                await email_service.send_employee_password_email(email, uid, password)
            except Exception as e:
                logger.warning(f'Failed to send password email to {email}: {e}')

    # Build response
    results = [
        CsvUploadResultItem(
            row=r.row,
            idno=r.idno,
            success=r.success,
            message=r.message,
        )
        for r in import_result.results
    ]
    success_count = sum(1 for r in results if r.success)

    return CsvUploadResponse(
        total=len(results),
        success_count=success_count,
        failure_count=len(results) - success_count,
        results=results,
    )
