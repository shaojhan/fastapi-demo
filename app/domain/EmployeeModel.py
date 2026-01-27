from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List


class Department(str, Enum):
    """
    Enumeration of available departments.

    HR: 人力資源部
    IT: 資訊科技部
    PR: 公關部
    RD: 研發部
    BD: 業務部
    """
    HR = 'HR'
    IT = 'IT'
    PR = 'PR'
    RD = 'RD'
    BD = 'BD'


@dataclass
class RoleInfo:
    """
    A Value Object representing role information for an employee.
    """
    id: int
    name: str
    level: int
    authorities: List[str]  # List of authority names


@dataclass
class EmployeeModel:
    """
    An Aggregate Root representing an employee in the domain.
    Employees have a role which determines their permissions through authorities.
    """
    id: int | None
    idno: str  # Employee ID number (unique identifier)
    department: Department
    user_id: str | None = None  # UUID string of linked user
    role: RoleInfo | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(idno: str, department: Department | str, user_id: str | None = None) -> "EmployeeModel":
        """
        Factory method to create a new employee.

        Args:
            idno: Employee identification number (must be unique)
            department: The department the employee belongs to
            user_id: Optional UUID string of the linked user

        Returns:
            A new EmployeeModel instance

        Raises:
            ValueError: If idno is empty or department is invalid
        """
        if not idno or not idno.strip():
            raise ValueError("Employee ID number cannot be empty")

        # Convert string to Department enum if necessary
        if isinstance(department, str):
            try:
                department = Department(department.upper())
            except ValueError:
                raise ValueError(f"Invalid department: {department}")

        return EmployeeModel(
            id=None,  # ID will be assigned by the database
            idno=idno.strip(),
            department=department,
            user_id=user_id,
            role=None,
            created_at=datetime.now(),
            updated_at=None
        )

    def assign_role(self, role_id: int, role_name: str, role_level: int, authorities: List[str]):
        """
        Assign a role to the employee.

        Args:
            role_id: The ID of the role
            role_name: The name of the role
            role_level: The level of the role
            authorities: List of authority names associated with the role
        """
        self.role = RoleInfo(
            id=role_id,
            name=role_name,
            level=role_level,
            authorities=authorities
        )
        self.updated_at = datetime.now()

    def change_department(self, department: Department | str):
        """
        Change the employee's department.

        Args:
            department: The new department

        Raises:
            ValueError: If department is invalid
        """
        # Convert string to Department enum if necessary
        if isinstance(department, str):
            try:
                department = Department(department.upper())
            except ValueError:
                raise ValueError(f"Invalid department: {department}")

        self.department = department
        self.updated_at = datetime.now()

    def has_authority(self, authority_name: str) -> bool:
        """
        Check if the employee has a specific authority.

        Args:
            authority_name: The name of the authority to check

        Returns:
            True if the employee has the authority, False otherwise
        """
        if not self.role:
            return False
        return authority_name in self.role.authorities

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EmployeeModel):
            return NotImplemented
        return self.idno == other.idno

    def __hash__(self) -> int:
        return hash(self.idno)
