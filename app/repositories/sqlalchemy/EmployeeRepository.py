from typing import Optional, List
from .BaseRepository import BaseRepository
from database.models.employee import Employee
from database.models.role import Role
from app.domain.EmployeeModel import EmployeeModel, RoleInfo, Department


class EmployeeRepository(BaseRepository):
    """
    Repository for persisting and retrieving Employee aggregates.
    Handles the mapping between domain models and database entities.
    """

    def add(self, employee_model: EmployeeModel) -> EmployeeModel:
        """
        Add a new employee to the database.

        Args:
            employee_model: The employee domain model to persist

        Returns:
            The employee domain model with assigned ID
        """
        employee_entity = Employee(
            idno=employee_model.idno,
            department=employee_model.department.value,
            role_id=employee_model.role.id if employee_model.role else None,
            created_at=employee_model.created_at,
            updated_at=employee_model.updated_at
        )

        self.db.add(employee_entity)
        self.db.flush()
        self.db.refresh(employee_entity)

        return self._to_domain_model(employee_entity)

    def get_by_id(self, employee_id: int) -> Optional[EmployeeModel]:
        """
        Retrieve an employee by ID.

        Args:
            employee_id: The employee's database ID

        Returns:
            The employee domain model or None if not found
        """
        employee_entity = self.db.query(Employee).filter(Employee.id == employee_id).first()

        if not employee_entity:
            return None

        return self._to_domain_model(employee_entity)

    def get_by_idno(self, idno: str) -> Optional[EmployeeModel]:
        """
        Retrieve an employee by their ID number.

        Args:
            idno: The employee's ID number

        Returns:
            The employee domain model or None if not found
        """
        employee_entity = self.db.query(Employee).filter(Employee.idno == idno).first()

        if not employee_entity:
            return None

        return self._to_domain_model(employee_entity)

    def get_all(self) -> List[EmployeeModel]:
        """
        Retrieve all employees.

        Returns:
            List of employee domain models
        """
        employee_entities = self.db.query(Employee).all()
        return [self._to_domain_model(e) for e in employee_entities]

    def get_by_department(self, department: Department) -> List[EmployeeModel]:
        """
        Retrieve all employees in a specific department.

        Args:
            department: The department to filter by

        Returns:
            List of employee domain models
        """
        employee_entities = self.db.query(Employee).filter(
            Employee.department == department.value
        ).all()
        return [self._to_domain_model(e) for e in employee_entities]

    def update(self, employee_model: EmployeeModel) -> EmployeeModel:
        """
        Update an existing employee.

        Args:
            employee_model: The employee domain model with updated data

        Returns:
            The updated employee domain model
        """
        employee_entity = self.db.query(Employee).filter(
            Employee.id == employee_model.id
        ).first()

        if not employee_entity:
            raise ValueError(f"Employee with id {employee_model.id} not found")

        employee_entity.idno = employee_model.idno
        employee_entity.department = employee_model.department.value
        employee_entity.role_id = employee_model.role.id if employee_model.role else None
        employee_entity.updated_at = employee_model.updated_at

        self.db.flush()
        self.db.refresh(employee_entity)

        return self._to_domain_model(employee_entity)

    def delete(self, employee_id: int) -> bool:
        """
        Delete an employee by ID.

        Args:
            employee_id: The employee's database ID

        Returns:
            True if deleted, False if not found
        """
        employee_entity = self.db.query(Employee).filter(Employee.id == employee_id).first()

        if not employee_entity:
            return False

        self.db.delete(employee_entity)
        self.db.flush()
        return True

    def exists_by_idno(self, idno: str) -> bool:
        """
        Check if an employee with the given ID number exists.

        Args:
            idno: The employee's ID number

        Returns:
            True if exists, False otherwise
        """
        return self.db.query(Employee).filter(Employee.idno == idno).first() is not None

    def _to_domain_model(self, employee_entity: Employee) -> EmployeeModel:
        """
        Convert a database entity to a domain model.

        Args:
            employee_entity: The database entity

        Returns:
            The employee domain model
        """
        role_info = None
        if employee_entity.role:
            authorities = [auth.name for auth in employee_entity.role.authorities]
            role_info = RoleInfo(
                id=employee_entity.role.id,
                name=employee_entity.role.name,
                level=employee_entity.role.level,
                authorities=authorities
            )

        return EmployeeModel(
            id=employee_entity.id,
            idno=employee_entity.idno,
            department=Department(employee_entity.department),
            role=role_info,
            created_at=employee_entity.created_at,
            updated_at=employee_entity.updated_at
        )


class EmployeeQueryRepository(BaseRepository):
    """
    Repository for read-only queries on employees.
    Can be optimized for specific query patterns.
    """

    def get_employees_with_authority(self, authority_name: str) -> List[EmployeeModel]:
        """
        Get all employees who have a specific authority.

        Args:
            authority_name: The name of the authority

        Returns:
            List of employee domain models
        """
        employees = self.db.query(Employee).join(Employee.role).join(Role.authorities).filter(
            Role.authorities.any(name=authority_name)
        ).all()

        return [self._to_domain_model(e) for e in employees]

    def _to_domain_model(self, employee_entity: Employee) -> EmployeeModel:
        """
        Convert a database entity to a domain model.

        Args:
            employee_entity: The database entity

        Returns:
            The employee domain model
        """
        role_info = None
        if employee_entity.role:
            authorities = [auth.name for auth in employee_entity.role.authorities]
            role_info = RoleInfo(
                id=employee_entity.role.id,
                name=employee_entity.role.name,
                level=employee_entity.role.level,
                authorities=authorities
            )

        return EmployeeModel(
            id=employee_entity.id,
            idno=employee_entity.idno,
            department=Department(employee_entity.department),
            role=role_info,
            created_at=employee_entity.created_at,
            updated_at=employee_entity.updated_at
        )
