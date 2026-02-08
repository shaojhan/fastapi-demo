from app.exceptions.BaseException import BaseException


class ScheduleException(BaseException):
    """Schedule related exception base class"""

    def __init__(self, message: str | None = None, name: str | None = "Schedule"):
        super().__init__(message=message, name=name)


class ScheduleNotFoundError(ScheduleException):
    """Schedule not found"""
    status_code = 404
    default_message = 'Schedule not found.'


class ScheduleAccessDeniedError(ScheduleException):
    """No permission to modify this schedule"""
    status_code = 403
    default_message = 'You do not have permission to modify this schedule.'


class InvalidScheduleTimeError(ScheduleException):
    """Invalid schedule time range"""
    status_code = 400
    default_message = 'Start time must be before end time.'


class GoogleCalendarNotConfiguredError(ScheduleException):
    """Google Calendar is not configured"""
    status_code = 400
    default_message = 'Google Calendar is not configured. Please configure it first.'


class GoogleCalendarSyncError(ScheduleException):
    """Error syncing with Google Calendar"""
    status_code = 500
    default_message = 'Failed to sync with Google Calendar.'
