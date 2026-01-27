from ..exceptions.BaseException import BaseException


class EmployeeException(BaseException):
    """Employee exception error"""

    def __init__(self, message: str | None = None, name: str | None = "Employee"):
        super().__init__(message=message, name=name)


class EmployeeAlreadyAssignedError(EmployeeException):
    """User is already assigned as an employee"""
    status_code = 409
    default_message = 'This user is already assigned as an employee.'


class EmployeeIdnoAlreadyExistsError(EmployeeException):
    """Employee ID number already exists"""
    status_code = 409
    default_message = 'An employee with this ID number already exists.'
