from app.exceptions.BaseException import BaseException


class ApprovalException(BaseException):
    """Approval related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "Approval"):
        super().__init__(message=message, name=name)


class ApprovalNotFoundError(ApprovalException):
    """Approval request not found"""
    status_code = 404
    default_message = 'Approval request not found.'


class ApprovalNotAuthorizedError(ApprovalException):
    """No permission to perform this action on the approval"""
    status_code = 403
    default_message = 'You are not authorized to perform this action on this approval.'


class ApprovalInvalidStatusError(ApprovalException):
    """Invalid status transition"""
    status_code = 400
    default_message = 'Invalid status transition for this approval request.'


class ApprovalChainError(ApprovalException):
    """Unable to build approval chain"""
    status_code = 400
    default_message = 'Unable to build approval chain. No suitable approvers found.'
