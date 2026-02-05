from dataclasses import dataclass, field
from typing import List

from app.domain.EmployeeModel import Department


@dataclass(frozen=True)
class EmployeeCsvRow:
    """
    Value Object representing a single validated CSV row for employee import.
    Use the `from_dict` factory method to create instances with validation.
    """
    idno: str
    department: Department
    email: str
    uid: str
    role_id: int | None

    @staticmethod
    def from_dict(row: dict) -> "EmployeeCsvRow":
        """
        Factory method to parse and validate a raw CSV dict.

        Args:
            row: Dictionary from csv.DictReader

        Returns:
            A validated EmployeeCsvRow

        Raises:
            ValueError: If required fields are missing or values are invalid
        """
        idno = (row.get('idno') or '').strip()
        department_str = (row.get('department') or '').strip()
        email = (row.get('email') or '').strip()
        uid = (row.get('uid') or '').strip()
        role_id_str = (row.get('role_id') or '').strip()

        if not idno:
            raise ValueError('idno is required')
        if not department_str:
            raise ValueError('department is required')
        if not email:
            raise ValueError('email is required')
        if not uid:
            raise ValueError('uid is required')

        try:
            department = Department(department_str.upper())
        except ValueError:
            raise ValueError(f'Invalid department: {department_str}')

        role_id: int | None = None
        if role_id_str:
            try:
                role_id = int(role_id_str)
            except ValueError:
                raise ValueError(f'Invalid role_id: {role_id_str}')

        return EmployeeCsvRow(
            idno=idno,
            department=department,
            email=email,
            uid=uid,
            role_id=role_id,
        )


@dataclass
class RowResult:
    """Result of processing a single CSV row."""
    row: int
    idno: str
    success: bool
    message: str

    @staticmethod
    def ok(row: int, idno: str) -> "RowResult":
        return RowResult(row=row, idno=idno, success=True, message='OK')

    @staticmethod
    def fail(row: int, idno: str, message: str) -> "RowResult":
        return RowResult(row=row, idno=idno, success=False, message=message)


@dataclass
class CsvImportResult:
    """Aggregate result of a CSV batch import."""
    results: List[RowResult] = field(default_factory=list)
    new_user_credentials: List[tuple[str, str, str]] = field(default_factory=list)  # (email, uid, password)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)
