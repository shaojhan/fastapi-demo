from datetime import datetime
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# === Request Schema ===

class CreateScheduleRequest(BaseModel):
    """Request schema for creating a schedule."""
    title: str = Field(..., min_length=1, max_length=255, description='Title')
    description: str | None = Field(None, description='Description')
    location: str | None = Field(None, max_length=512, description='Location')
    start_time: datetime = Field(..., description='Start time')
    end_time: datetime = Field(..., description='End time')
    all_day: bool = Field(False, description='Whether this is an all-day event')
    timezone: str = Field('Asia/Taipei', description='Timezone')
    sync_to_google: bool = Field(True, description='Whether to sync to Google Calendar')

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'title': 'Team Meeting',
                    'description': 'Weekly team sync meeting',
                    'location': 'Conference Room A',
                    'start_time': '2024-01-15T09:00:00',
                    'end_time': '2024-01-15T10:00:00',
                    'all_day': False,
                    'timezone': 'Asia/Taipei',
                    'sync_to_google': True
                }
            ]
        }
    }


class UpdateScheduleRequest(BaseModel):
    """Request schema for updating a schedule."""
    title: str | None = Field(None, min_length=1, max_length=255, description='Title')
    description: str | None = Field(None, description='Description')
    location: str | None = Field(None, max_length=512, description='Location')
    start_time: datetime | None = Field(None, description='Start time')
    end_time: datetime | None = Field(None, description='End time')
    all_day: bool | None = Field(None, description='Whether this is an all-day event')
    timezone: str | None = Field(None, description='Timezone')
    sync_to_google: bool = Field(True, description='Whether to sync to Google Calendar')


class ConnectGoogleRequest(BaseModel):
    """Request schema for connecting Google Calendar."""
    calendar_id: str = Field(..., description='Google Calendar ID')
    access_token: str = Field(..., description='OAuth access token')
    refresh_token: str = Field(..., description='OAuth refresh token')
    expires_at: datetime = Field(..., description='Token expiration time')


# === Response Schema ===

class ScheduleCreatorResponse(BaseModel):
    """Schedule creator info."""
    user_id: UUID
    username: str
    email: str


class GoogleSyncResponse(BaseModel):
    """Google Calendar sync info."""
    event_id: str | None = None
    synced_at: datetime | None = None
    is_synced: bool = False


class ScheduleResponse(BaseModel):
    """Single schedule response."""
    id: UUID
    title: str
    description: str | None = None
    location: str | None = None
    start_time: datetime
    end_time: datetime
    all_day: bool
    timezone: str
    creator: ScheduleCreatorResponse | None = None
    google_sync: GoogleSyncResponse
    created_at: datetime
    updated_at: datetime | None = None


class ScheduleListItem(BaseModel):
    """Schedule list item."""
    id: UUID
    title: str
    description: str | None = None
    location: str | None = None
    start_time: datetime
    end_time: datetime
    all_day: bool
    creator: ScheduleCreatorResponse | None = None
    is_synced: bool = False
    created_at: datetime


class ScheduleListResponse(BaseModel):
    """Paginated schedule list response."""
    items: list[ScheduleListItem]
    total: int
    page: int
    size: int


class GoogleStatusResponse(BaseModel):
    """Google Calendar connection status."""
    connected: bool
    calendar_id: str | None = None
    expires_at: datetime | None = None


class ScheduleActionResponse(BaseModel):
    """Action result response."""
    message: str
    success: bool = True


class GoogleAuthUrlResponse(BaseModel):
    """Google OAuth authorization URL response."""
    auth_url: str
    message: str = "Please visit the URL to authorize Google Calendar access"


class GoogleCalendarListItem(BaseModel):
    """Google Calendar list item."""
    id: str
    summary: str
    description: str | None = None
    primary: bool = False


class GoogleCalendarListResponse(BaseModel):
    """List of available Google Calendars."""
    calendars: list[GoogleCalendarListItem]
    message: str = "Select a calendar to connect"
