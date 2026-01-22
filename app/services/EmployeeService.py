from typing import Optional, List
from app.domain.EmployeeModel import EmployeeModel, Department
from app.services.unitofwork.EmployeeUnitOfWork import EmployeeUnitOfWork, EmployeeQueryUnitOfWork


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
