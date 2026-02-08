"""
Google Calendar API Service.

Handles creating, updating, and deleting events in Google Calendar.
Includes OAuth 2.0 authorization flow for Calendar access.
"""

from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.domain.ScheduleModel import ScheduleModel

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarService:
    """Service for Google Calendar API operations."""

    def __init__(self):
        self._settings = get_settings()

    def _format_datetime(self, dt: datetime, all_day: bool, timezone: str) -> dict:
        """Format datetime for Google Calendar API."""
        if all_day:
            return {"date": dt.strftime("%Y-%m-%d")}
        return {
            "dateTime": dt.isoformat(),
            "timeZone": timezone,
        }

    async def create_event(
        self,
        access_token: str,
        calendar_id: str,
        schedule: ScheduleModel
    ) -> str:
        """
        Create an event in Google Calendar.

        Args:
            access_token: OAuth access token
            calendar_id: Google Calendar ID
            schedule: The schedule to create

        Returns:
            Google Calendar event ID

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        event_body = {
            "summary": schedule.title,
            "description": schedule.description,
            "location": schedule.location,
            "start": self._format_datetime(
                schedule.start_time,
                schedule.all_day,
                schedule.timezone
            ),
            "end": self._format_datetime(
                schedule.end_time,
                schedule.all_day,
                schedule.timezone
            ),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body,
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def update_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        schedule: ScheduleModel
    ) -> str:
        """
        Update an event in Google Calendar.

        Args:
            access_token: OAuth access token
            calendar_id: Google Calendar ID
            event_id: Google Calendar event ID
            schedule: The updated schedule

        Returns:
            Google Calendar event ID

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        event_body = {
            "summary": schedule.title,
            "description": schedule.description,
            "location": schedule.location,
            "start": self._format_datetime(
                schedule.start_time,
                schedule.all_day,
                schedule.timezone
            ),
            "end": self._format_datetime(
                schedule.end_time,
                schedule.all_day,
                schedule.timezone
            ),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body,
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> None:
        """
        Delete an event from Google Calendar.

        Args:
            access_token: OAuth access token
            calendar_id: Google Calendar ID
            event_id: Google Calendar event ID

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{GOOGLE_CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            # 404 is ok (already deleted)
            if resp.status_code != 404:
                resp.raise_for_status()

    def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an OAuth access token.

        Args:
            refresh_token: The refresh token

        Returns:
            Dict with access_token, expires_at, and optionally refresh_token

        Raises:
            httpx.HTTPStatusError: If refresh fails
        """
        import httpx as sync_httpx

        resp = sync_httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self._settings.GOOGLE_CLIENT_ID,
                "client_secret": self._settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()

        data = resp.json()
        expires_in = data.get("expires_in", 3600)

        return {
            "access_token": data["access_token"],
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
            "refresh_token": data.get("refresh_token"),  # May not be returned
        }

    async def get_calendar_list(self, access_token: str) -> list:
        """
        Get list of calendars for the authenticated user.

        Args:
            access_token: OAuth access token

        Returns:
            List of calendar info dicts

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GOOGLE_CALENDAR_API_BASE}/users/me/calendarList",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json().get("items", [])

    def get_authorization_url(self, state: str | None = None) -> str:
        """
        Generate OAuth 2.0 authorization URL for Google Calendar.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self._settings.GOOGLE_CLIENT_ID,
            "redirect_uri": self._settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "response_type": "code",
            "scope": self._settings.GOOGLE_CALENDAR_SCOPES,
            "access_type": "offline",  # Required for refresh_token
            "prompt": "consent",  # Force consent to get refresh_token
        }
        if state:
            params["state"] = state

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with access_token, refresh_token, expires_at

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self._settings.GOOGLE_CLIENT_ID,
                "client_secret": self._settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._settings.GOOGLE_CALENDAR_REDIRECT_URI,
            },
        )
        resp.raise_for_status()

        data = resp.json()
        expires_in = data.get("expires_in", 3600)

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
        }
