import secrets
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from passlib.context import CryptContext

from app.domain.EmployeeModel import EmployeeModel, Department
from app.domain.EmployeeCsvImportModel import EmployeeCsvRow, RowResult, CsvImportResult
from app.domain.UserModel import UserRole
from app.services.unitofwork.EmployeeUnitOfWork import EmployeeUnitOfWork, EmployeeQueryUnitOfWork
from app.services.unitofwork.AssignEmployeeUnitOfWork import AssignEmployeeUnitOfWork
from app.exceptions.UserException import UserNotFoundError
from app.exceptions.EmployeeException import EmployeeAlreadyAssignedError, EmployeeIdnoAlreadyExistsError


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class EmployeeService:
    """
    Application service for Employee aggregate.
    Orchestrates domain logic and persistence operations.
    """

    def create_employee(self, idno: str, department: Department | str) -> EmployeeModel:
        """
        Create a new employee.

        Args:
            idno: Employee identification number
            department: Department enum or string

        Returns:
            The created employee domain model

        Raises:
            ValueError: If idno already exists or is invalid
        """
        # Check if employee already exists
        with EmployeeUnitOfWork() as uow:
            if uow.repo.exists_by_idno(idno):
                raise ValueError(f"Employee with ID number '{idno}' already exists")

            # Use domain factory method to create employee
            employee = EmployeeModel.create(idno=idno, department=department)

            # Persist the employee
            created_employee = uow.repo.add(employee)
            uow.commit()

            return created_employee

    def get_employee_by_id(self, employee_id: int) -> Optional[EmployeeModel]:
        """
        Retrieve an employee by their database ID.

        Args:
            employee_id: The employee's database ID

        Returns:
            Employee domain model or None if not found
        """
        with EmployeeUnitOfWork() as uow:
            return uow.repo.get_by_id(employee_id)

    def get_employee_by_idno(self, idno: str) -> Optional[EmployeeModel]:
        """
        Retrieve an employee by their ID number.

        Args:
            idno: The employee's ID number

        Returns:
            Employee domain model or None if not found
        """
        with EmployeeUnitOfWork() as uow:
            return uow.repo.get_by_idno(idno)

    def get_all_employees(self) -> List[EmployeeModel]:
        """
        Retrieve all employees.

        Returns:
            List of employee domain models
        """
        with EmployeeUnitOfWork() as uow:
            return uow.repo.get_all()

    def get_employees_by_department(self, department: Department | str) -> List[EmployeeModel]:
        """
        Retrieve all employees in a specific department.

        Args:
            department: Department enum or string

        Returns:
            List of employee domain models
        """
        # Convert string to Department enum if necessary
        if isinstance(department, str):
            department = Department(department.upper())

        with EmployeeUnitOfWork() as uow:
            return uow.repo.get_by_department(department)

    def assign_role_to_employee(
        self,
        employee_id: int,
        role_id: int,
        role_name: str,
        role_level: int,
        authorities: List[str]
    ) -> EmployeeModel:
        """
        Assign a role to an employee.

        Args:
            employee_id: The employee's database ID
            role_id: The role's database ID
            role_name: The role name
            role_level: The role level
            authorities: List of authority names

        Returns:
            Updated employee domain model

        Raises:
            ValueError: If employee not found
        """
        with EmployeeUnitOfWork() as uow:
            employee = uow.repo.get_by_id(employee_id)

            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            # Use domain method to assign role
            employee.assign_role(
                role_id=role_id,
                role_name=role_name,
                role_level=role_level,
                authorities=authorities
            )

            # Persist the changes
            updated_employee = uow.repo.update(employee)
            uow.commit()

            return updated_employee

    def change_employee_department(
        self,
        employee_id: int,
        new_department: Department | str
    ) -> EmployeeModel:
        """
        Change an employee's department.

        Args:
            employee_id: The employee's database ID
            new_department: The new department (enum or string)

        Returns:
            Updated employee domain model

        Raises:
            ValueError: If employee not found or department invalid
        """
        with EmployeeUnitOfWork() as uow:
            employee = uow.repo.get_by_id(employee_id)

            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            # Use domain method to change department
            employee.change_department(new_department)

            # Persist the changes
            updated_employee = uow.repo.update(employee)
            uow.commit()

            return updated_employee

    def delete_employee(self, employee_id: int) -> bool:
        """
        Delete an employee.

        Args:
            employee_id: The employee's database ID

        Returns:
            True if deleted, False if not found
        """
        with EmployeeUnitOfWork() as uow:
            deleted = uow.repo.delete(employee_id)
            uow.commit()
            return deleted

    def assign_user_as_employee(
        self,
        user_id: str,
        idno: str,
        department: Department | str,
        role_id: int | None = None
    ) -> EmployeeModel:
        """
        Assign an existing user as an employee.
        Cross-aggregate operation: creates Employee and updates User role atomically.

        Args:
            user_id: The UUID of the user to assign
            idno: Employee identification number
            department: Department enum or string
            role_id: Optional role ID to assign

        Returns:
            The created EmployeeModel

        Raises:
            UserNotFoundError: If the user does not exist
            EmployeeAlreadyAssignedError: If the user already has an employee record
            EmployeeIdnoAlreadyExistsError: If the idno is already in use
            ValueError: If idno or department is invalid
        """
        with AssignEmployeeUnitOfWork() as uow:
            # Verify user exists
            user = uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError()

            # Verify user is not already an employee
            if uow.employee_repo.exists_by_user_id(user_id):
                raise EmployeeAlreadyAssignedError()

            # Verify idno is not already taken
            if uow.employee_repo.exists_by_idno(idno):
                raise EmployeeIdnoAlreadyExistsError()

            # Domain validation: promote user role
            user.promote_to_employee()

            # Create employee via domain factory
            employee = EmployeeModel.create(
                idno=idno,
                department=department,
                user_id=user_id
            )

            # Assign role if role_id provided
            if role_id:
                role_entity = uow.employee_repo.get_role_by_id(role_id)
                if role_entity:
                    employee.assign_role(
                        role_id=role_entity.id,
                        role_name=role_entity.name,
                        role_level=role_entity.level,
                        authorities=[auth.name for auth in role_entity.authorities]
                    )

            # Persist employee
            created_employee = uow.employee_repo.add(employee)

            # Persist user role change
            uow.user_repo.update_role(user_id, UserRole.EMPLOYEE)

            uow.commit()
            return created_employee

    def batch_import_employees(self, rows: List[dict]) -> CsvImportResult:
        """
        Batch import employees from parsed CSV rows.
        For each row, auto-creates a user account if one doesn't exist,
        then assigns the user as an employee.

        Each row is processed in its own transaction so failures don't
        affect other rows.

        Args:
            rows: List of dicts with keys: idno, department, email, uid, role_id

        Returns:
            CsvImportResult with per-row results and new user credentials
        """
        result = CsvImportResult()

        for idx, row in enumerate(rows, start=1):
            # Validate via domain model
            try:
                csv_row = EmployeeCsvRow.from_dict(row)
            except ValueError as e:
                idno = (row.get('idno') or '').strip() or '(empty)'
                result.results.append(RowResult.fail(row=idx, idno=idno, message=str(e)))
                continue

            # Process in its own transaction
            try:
                new_password = self._import_single_employee(csv_row)
                if new_password:
                    result.new_user_credentials.append((csv_row.email, csv_row.uid, new_password))
                result.results.append(RowResult.ok(row=idx, idno=csv_row.idno))
            except Exception as e:
                result.results.append(RowResult.fail(row=idx, idno=csv_row.idno, message=str(e)))

        return result

    def _import_single_employee(self, csv_row: EmployeeCsvRow) -> str | None:
        """
        Import a single employee row within one transaction.

        Args:
            csv_row: Validated CSV row domain object

        Returns:
            The plain-text password if a new user was created, None otherwise.
        """
        with AssignEmployeeUnitOfWork() as uow:
            # Check idno uniqueness
            if uow.employee_repo.exists_by_idno(csv_row.idno):
                raise ValueError(f'Employee ID number {csv_row.idno} already exists')

            # Look up existing user by uid or email
            user = uow.user_repo.get_by_uid(csv_row.uid)
            if not user:
                user = uow.user_repo.get_by_email(csv_row.email)

            new_password: str | None = None

            if user:
                # User exists — check if already an employee
                if uow.employee_repo.exists_by_user_id(user.id):
                    raise ValueError(f'User {csv_row.uid} is already assigned as an employee')
                user_id = user.id
            else:
                # Create new user account
                new_password = secrets.token_urlsafe(12)
                now = datetime.now(tz=timezone.utc)
                user_id = str(uuid4())

                user_dict = {
                    'id': user_id,
                    'created_at': now,
                    'uid': csv_row.uid,
                    'pwd': pwd_context.hash(new_password),
                    'email': csv_row.email,
                    'role': UserRole.NORMAL,
                    'email_verified': True,
                }
                profile_dict = {
                    'name': '',
                    'created_at': now,
                    'birthdate': None,
                    'description': '',
                }
                uow.user_repo.add(user_dict, profile_dict)

            # Promote user to EMPLOYEE role
            uow.user_repo.update_role(user_id, UserRole.EMPLOYEE)

            # Create employee record
            employee = EmployeeModel.create(
                idno=csv_row.idno,
                department=csv_row.department,
                user_id=user_id,
            )

            # Assign role if provided
            if csv_row.role_id:
                role_entity = uow.employee_repo.get_role_by_id(csv_row.role_id)
                if role_entity:
                    employee.assign_role(
                        role_id=role_entity.id,
                        role_name=role_entity.name,
                        role_level=role_entity.level,
                        authorities=[auth.name for auth in role_entity.authorities],
                    )

            uow.employee_repo.add(employee)
            uow.commit()

            return new_password

    def check_employee_authority(self, employee_id: int, authority_name: str) -> bool:
        """
        Check if an employee has a specific authority.

        Args:
            employee_id: The employee's database ID
            authority_name: The authority name to check

        Returns:
            True if employee has the authority, False otherwise

        Raises:
            ValueError: If employee not found
        """
        with EmployeeUnitOfWork() as uow:
            employee = uow.repo.get_by_id(employee_id)

            if not employee:
                raise ValueError(f"Employee with ID {employee_id} not found")

            # Use domain method to check authority
            return employee.has_authority(authority_name)


class EmployeeQueryService:
    """
    Query service for read-only employee operations.
    Provides optimized queries for specific use cases.
    """

    def get_all_employees_paginated(self, page: int, size: int):
        """Get paginated list of all employees."""
        with EmployeeQueryUnitOfWork() as uow:
            return uow.query_repo.get_all_paginated(page, size)

    def get_employees_with_authority(self, authority_name: str) -> List[EmployeeModel]:
        """
        Get all employees who have a specific authority.

        Args:
            authority_name: The authority name

        Returns:
            List of employee domain models
        """
        with EmployeeQueryUnitOfWork() as uow:
            return uow.query_repo.get_employees_with_authority(authority_name)

    def get_employees_by_role_level(self, min_level: int) -> List[EmployeeModel]:
        """
        Get all employees with a role level at or above the specified minimum.

        Args:
            min_level: The minimum role level

        Returns:
            List of employee domain models
        """
        with EmployeeUnitOfWork() as uow:
            all_employees = uow.repo.get_all()
            return [
                emp for emp in all_employees
                if emp.role and emp.role.level >= min_level
            ]

    def get_department_statistics(self) -> dict:
        """
        Get statistics about employees by department.

        Returns:
            Dictionary with department counts
        """
        with EmployeeUnitOfWork() as uow:
            all_employees = uow.repo.get_all()

            stats = {}
            for dept in Department:
                stats[dept.value] = sum(1 for emp in all_employees if emp.department == dept)

            return stats
