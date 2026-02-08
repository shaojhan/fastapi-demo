from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import RedirectResponse
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.router.schemas.ScheduleSchema import (
    CreateScheduleRequest,
    UpdateScheduleRequest,
    ConnectGoogleRequest,
    ScheduleResponse,
    ScheduleListItem,
    ScheduleListResponse,
    ScheduleCreatorResponse,
    GoogleSyncResponse,
    GoogleStatusResponse,
    ScheduleActionResponse,
    GoogleAuthUrlResponse,
    GoogleCalendarListItem,
    GoogleCalendarListResponse,
)
from app.services.ScheduleService import ScheduleService
from app.services.GoogleCalendarService import GoogleCalendarService
from app.domain.UserModel import UserModel
from app.router.dependencies.auth import get_current_user, require_employee, require_admin
from app.config import get_settings


router = APIRouter(prefix='/schedules', tags=['schedule'])


def get_schedule_service() -> ScheduleService:
    return ScheduleService()


def get_google_calendar_service() -> GoogleCalendarService:
    return GoogleCalendarService()


# Temporary storage for OAuth state (in production, use Redis/DB)
_oauth_states: dict[str, dict] = {}


def _to_creator_response(creator) -> Optional[ScheduleCreatorResponse]:
    """Convert creator to response format."""
    if not creator:
        return None
    return ScheduleCreatorResponse(
        user_id=UUID(creator.user_id),
        username=creator.username,
        email=creator.email
    )


def _to_schedule_response(schedule) -> ScheduleResponse:
    """Convert schedule to response format."""
    return ScheduleResponse(
        id=UUID(schedule.id),
        title=schedule.title,
        description=schedule.description,
        location=schedule.location,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        all_day=schedule.all_day,
        timezone=schedule.timezone,
        creator=_to_creator_response(schedule.creator),
        google_sync=GoogleSyncResponse(
            event_id=schedule.google_event_id,
            synced_at=schedule.synced_at,
            is_synced=schedule.google_sync.is_synced
        ),
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )


def _to_list_item(schedule) -> ScheduleListItem:
    """Convert schedule to list item format."""
    return ScheduleListItem(
        id=UUID(schedule.id),
        title=schedule.title,
        description=schedule.description,
        location=schedule.location,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        all_day=schedule.all_day,
        creator=_to_creator_response(schedule.creator),
        is_synced=schedule.google_sync.is_synced,
        created_at=schedule.created_at
    )


@router.post('/', response_model=ScheduleResponse, operation_id='create_schedule')
async def create_schedule(
    request_body: CreateScheduleRequest,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleResponse:
    """Create a new schedule. Only employees can create schedules."""
    schedule = service.create_schedule(
        creator_id=current_user.id,
        title=request_body.title,
        description=request_body.description,
        location=request_body.location,
        start_time=request_body.start_time,
        end_time=request_body.end_time,
        all_day=request_body.all_day,
        timezone=request_body.timezone,
        sync_to_google=request_body.sync_to_google,
    )
    return _to_schedule_response(schedule)


@router.get('/', response_model=ScheduleListResponse, operation_id='list_schedules')
async def list_schedules(
    page: int = Query(1, ge=1, description='Page number'),
    size: int = Query(20, ge=1, le=100, description='Page size'),
    start_from: Optional[datetime] = Query(None, description='Filter schedules starting from this time'),
    start_to: Optional[datetime] = Query(None, description='Filter schedules starting before this time'),
    current_user: UserModel = Depends(require_employee),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleListResponse:
    """List all schedules. Only employees can view schedules."""
    schedules, total = service.list_schedules(
        page=page,
        size=size,
        start_from=start_from,
        start_to=start_to,
    )
    items = [_to_list_item(s) for s in schedules]
    return ScheduleListResponse(
        items=items,
        total=total,
        page=page,
        size=size
    )


@router.get('/google/status', response_model=GoogleStatusResponse, operation_id='get_google_status')
async def get_google_status(
    current_user: UserModel = Depends(require_admin),
    service: ScheduleService = Depends(get_schedule_service)
) -> GoogleStatusResponse:
    """Get Google Calendar connection status. Only admins can check status."""
    status = service.get_google_status()
    return GoogleStatusResponse(**status)


@router.get('/google/auth', response_model=GoogleAuthUrlResponse, operation_id='get_google_auth_url')
async def get_google_auth_url(
    current_user: UserModel = Depends(require_admin),
    google_service: GoogleCalendarService = Depends(get_google_calendar_service)
) -> GoogleAuthUrlResponse:
    """
    Get Google OAuth authorization URL.
    Admin will be redirected to Google to grant Calendar access.
    """
    # Generate state for CSRF protection
    state = str(uuid4())
    _oauth_states[state] = {
        "user_id": current_user.id,
        "created_at": datetime.utcnow()
    }

    auth_url = google_service.get_authorization_url(state=state)
    return GoogleAuthUrlResponse(auth_url=auth_url)


@router.get('/google/callback', operation_id='google_oauth_callback')
async def google_oauth_callback(
    code: str = Query(..., description='Authorization code from Google'),
    state: str = Query(..., description='State for CSRF protection'),
    error: Optional[str] = Query(None, description='Error from Google'),
    google_service: GoogleCalendarService = Depends(get_google_calendar_service),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    OAuth callback endpoint.
    Google redirects here after user grants/denies access.
    """
    settings = get_settings()

    # Check for errors from Google
    if error:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/admin/calendar?error={error}",
            status_code=302
        )

    # Validate state
    if state not in _oauth_states:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/admin/calendar?error=invalid_state",
            status_code=302
        )

    # Remove used state
    state_data = _oauth_states.pop(state)

    try:
        # Exchange code for tokens
        tokens = google_service.exchange_code_for_tokens(code)

        # Store tokens temporarily in session/state for calendar selection
        # For now, we'll store them and redirect to calendar selection
        temp_token_id = str(uuid4())
        _oauth_states[f"tokens_{temp_token_id}"] = {
            **tokens,
            "user_id": state_data["user_id"],
            "created_at": datetime.utcnow()
        }

        # Redirect to calendar selection page
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/admin/calendar/select?token_id={temp_token_id}",
            status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/admin/calendar?error=token_exchange_failed",
            status_code=302
        )


@router.get('/google/calendars', response_model=GoogleCalendarListResponse, operation_id='list_google_calendars')
async def list_google_calendars(
    token_id: str = Query(..., description='Temporary token ID from OAuth callback'),
    google_service: GoogleCalendarService = Depends(get_google_calendar_service)
) -> GoogleCalendarListResponse:
    """
    List available Google Calendars after OAuth authorization.
    Used to select which calendar to sync with.
    """
    token_key = f"tokens_{token_id}"
    if token_key not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired token_id")

    tokens = _oauth_states[token_key]

    try:
        calendars = await google_service.get_calendar_list(tokens["access_token"])

        items = [
            GoogleCalendarListItem(
                id=cal.get("id", ""),
                summary=cal.get("summary", "Unknown"),
                description=cal.get("description"),
                primary=cal.get("primary", False)
            )
            for cal in calendars
        ]

        return GoogleCalendarListResponse(calendars=items)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendars: {str(e)}")


@router.post('/google/calendars/{calendar_id}/select', response_model=GoogleStatusResponse, operation_id='select_google_calendar')
async def select_google_calendar(
    calendar_id: str,
    token_id: str = Query(..., description='Temporary token ID from OAuth callback'),
    current_user: UserModel = Depends(require_admin),
    schedule_service: ScheduleService = Depends(get_schedule_service)
) -> GoogleStatusResponse:
    """
    Select a Google Calendar and complete the connection.
    This saves the OAuth tokens and calendar ID to the database.
    """
    token_key = f"tokens_{token_id}"
    if token_key not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired token_id")

    tokens = _oauth_states.pop(token_key)

    # Verify the user is the same as who started the OAuth flow
    if tokens.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Token does not belong to current user")

    # Save the configuration
    result = schedule_service.connect_google(
        calendar_id=calendar_id,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_at=tokens["expires_at"]
    )

    return GoogleStatusResponse(**result)


@router.post('/google/connect', response_model=GoogleStatusResponse, operation_id='connect_google')
async def connect_google(
    request_body: ConnectGoogleRequest,
    current_user: UserModel = Depends(require_admin),
    service: ScheduleService = Depends(get_schedule_service)
) -> GoogleStatusResponse:
    """Connect Google Calendar. Only admins can configure."""
    result = service.connect_google(
        calendar_id=request_body.calendar_id,
        access_token=request_body.access_token,
        refresh_token=request_body.refresh_token,
        expires_at=request_body.expires_at,
    )
    return GoogleStatusResponse(**result)


@router.delete('/google/disconnect', response_model=ScheduleActionResponse, operation_id='disconnect_google')
async def disconnect_google(
    current_user: UserModel = Depends(require_admin),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleActionResponse:
    """Disconnect Google Calendar. Only admins can configure."""
    service.disconnect_google()
    return ScheduleActionResponse(message='Google Calendar disconnected.')


@router.get('/{schedule_id}', response_model=ScheduleResponse, operation_id='get_schedule')
async def get_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleResponse:
    """Get a single schedule detail. Only employees can view schedules."""
    schedule = service.get_schedule(schedule_id)
    return _to_schedule_response(schedule)


@router.put('/{schedule_id}', response_model=ScheduleResponse, operation_id='update_schedule')
async def update_schedule(
    schedule_id: str,
    request_body: UpdateScheduleRequest,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleResponse:
    """Update a schedule. Only the creator can update."""
    schedule = service.update_schedule(
        user_id=current_user.id,
        schedule_id=schedule_id,
        title=request_body.title,
        description=request_body.description,
        location=request_body.location,
        start_time=request_body.start_time,
        end_time=request_body.end_time,
        all_day=request_body.all_day,
        timezone=request_body.timezone,
        sync_to_google=request_body.sync_to_google,
    )
    return _to_schedule_response(schedule)


@router.delete('/{schedule_id}', response_model=ScheduleActionResponse, operation_id='delete_schedule')
async def delete_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleActionResponse:
    """Delete a schedule. Only the creator can delete."""
    service.delete_schedule(
        user_id=current_user.id,
        schedule_id=schedule_id
    )
    return ScheduleActionResponse(message='Schedule deleted.')


@router.post('/{schedule_id}/sync', response_model=ScheduleResponse, operation_id='sync_schedule')
async def sync_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(require_employee),
    service: ScheduleService = Depends(get_schedule_service)
) -> ScheduleResponse:
    """Manually sync a schedule to Google Calendar. Only the creator can sync."""
    schedule = service.sync_schedule(
        user_id=current_user.id,
        schedule_id=schedule_id
    )
    return _to_schedule_response(schedule)
