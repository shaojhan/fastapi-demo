from ..exceptions.BaseException import BaseException

class WorkflowException(BaseException):
    """Workflow exception error"""
    
    def __init__(self, message: str | None = None, name: str | None = "Workflow"):
        super().__init__(message=message, name=name)

class DataNotFoundError(WorkflowException):
    """Database returns nothing"""
    status_code = 404
    default_message = 'The workflow was not found.'


class AuthenticationError(WorkflowException):
    """invalid """