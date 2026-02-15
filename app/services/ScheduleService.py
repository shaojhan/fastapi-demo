from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Tuple, TYPE_CHECKING

from loguru import logger

from app.services.unitofwork.ScheduleUnitOfWork import (
    ScheduleUnitOfWork,
    ScheduleQueryUnitOfWork
)
from app.domain.ScheduleModel import ScheduleModel
from app.exceptions.ScheduleException import (
    ScheduleNotFoundError,
    ScheduleAccessDeniedError,
    GoogleCalendarNotConfiguredError,
    GoogleCalendarSyncError,
)

if TYPE_CHECKING:
    from app.router.schemas.ScheduleSchema import CreateScheduleRequest, UpdateScheduleRequest


class ScheduleService:
    """Application service for schedule management operations."""

    def create_schedule(
        self,
        creator_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str | None = None,
        location: str | None = None,
        all_day: bool = False,
        timezone: str = "Asia/Taipei",
        sync_to_google: bool = False,
    ) -> ScheduleModel:
        """
        Create a new schedule.

        Args:
            creator_id: Creator's UUID
            title: Schedule title
            start_time: Start time
            end_time: End time
            description: Optional description
            location: Optional location
            all_day: Whether this is an all-day event
            timezone: Timezone string
            sync_to_google: Whether to sync to Google Calendar

        Returns:
            The created schedule

        Raises:
            ValueError: If validation fails
            GoogleCalendarSyncError: If sync fails
        """
        schedule = ScheduleModel.create(
            title=title,
            start_time=start_time,
            end_time=end_time,
            creator_id=creator_id,
            description=description,
            location=location,
            all_day=all_day,
            timezone=timezone,
        )

        with ScheduleUnitOfWork() as uow:
            created_schedule = uow.repo.add(schedule)

            # Sync to Google Calendar if requested
            if sync_to_google:
                try:
                    google_event_id = self._sync_to_google(uow, created_schedule)
                    if google_event_id:
                        created_schedule.mark_synced(google_event_id)
                        uow.repo.update(created_schedule)
                        logger.info(f"Schedule synced to Google Calendar: {google_event_id}")
                except Exception as e:
                    logger.error(f"Failed to sync new schedule to Google: {e}")

            uow.commit()
            return created_schedule

    def get_schedule(self, schedule_id: str) -> ScheduleModel:
        """
        Get a schedule by ID.

        Args:
            schedule_id: The schedule UUID

        Returns:
            The schedule

        Raises:
            ScheduleNotFoundError: If schedule not found
        """
        with ScheduleQueryUnitOfWork() as uow:
            schedule = uow.repo.get_by_id(schedule_id)
            if not schedule:
                raise ScheduleNotFoundError()
            return schedule

    def list_schedules(
        self,
        page: int = 1,
        size: int = 20,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
    ) -> Tuple[List[ScheduleModel], int]:
        """
        List all schedules (paginated).

        Args:
            page: Page number
            size: Page size
            start_from: Filter schedules starting from this time
            start_to: Filter schedules starting before this time

        Returns:
            (list of schedules, total count)
        """
        with ScheduleQueryUnitOfWork() as uow:
            return uow.repo.get_all(page, size, start_from, start_to)

    def update_schedule(
        self,
        user_id: str,
        schedule_id: str,
        title: str | None = None,
        description: str | None = None,
        location: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        all_day: bool | None = None,
        timezone: str | None = None,
        sync_to_google: bool = False,
    ) -> ScheduleModel:
        """
        Update an existing schedule.

        Args:
            user_id: User attempting the update
            schedule_id: The schedule UUID
            title: New title (optional)
            description: New description (optional)
            location: New location (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            all_day: New all_day flag (optional)
            timezone: New timezone (optional)
            sync_to_google: Whether to sync to Google Calendar

        Returns:
            The updated schedule

        Raises:
            ScheduleNotFoundError: If schedule not found
            ScheduleAccessDeniedError: If user is not the creator
        """
        with ScheduleUnitOfWork() as uow:
            schedule = uow.repo.get_by_id(schedule_id)
            if not schedule:
                raise ScheduleNotFoundError()

            if not schedule.can_edit(user_id):
                raise ScheduleAccessDeniedError()

            schedule.update(
                title=title,
                description=description,
                location=location,
                start_time=start_time,
                end_time=end_time,
                all_day=all_day,
                timezone=timezone,
            )

            updated_schedule = uow.repo.update(schedule)

            # Sync to Google Calendar if requested
            if sync_to_google:
                try:
                    google_event_id = self._sync_to_google(uow, updated_schedule)
                    if google_event_id:
                        updated_schedule.mark_synced(google_event_id)
                        uow.repo.update(updated_schedule)
                        logger.info(f"Schedule synced to Google Calendar: {google_event_id}")
                except Exception as e:
                    logger.error(f"Failed to sync updated schedule to Google: {e}")

            uow.commit()
            return updated_schedule

    def delete_schedule(self, user_id: str, schedule_id: str) -> None:
        """
        Delete a schedule.

        Args:
            user_id: User attempting the deletion
            schedule_id: The schedule UUID

        Raises:
            ScheduleNotFoundError: If schedule not found
            ScheduleAccessDeniedError: If user is not the creator
        """
        with ScheduleUnitOfWork() as uow:
            schedule = uow.repo.get_by_id(schedule_id)
            if not schedule:
                raise ScheduleNotFoundError()

            if not schedule.can_edit(user_id):
                raise ScheduleAccessDeniedError()

            # Delete from Google Calendar if synced
            if schedule.google_event_id:
                try:
                    self._delete_from_google(uow, schedule.google_event_id)
                except Exception:
                    # Log error but continue with deletion
                    pass

            uow.repo.delete(schedule_id)
            uow.commit()

    def check_conflicts(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_id: str | None = None,
    ) -> List[ScheduleModel]:
        """
        Check for scheduling conflicts in the given time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range
            exclude_id: Schedule ID to exclude (for update scenarios)

        Returns:
            List of conflicting schedules
        """
        with ScheduleQueryUnitOfWork() as uow:
            return uow.repo.find_conflicts(start_time, end_time, exclude_id)

    def suggest_available_slots(
        self,
        date: datetime,
        duration_minutes: int = 60,
        work_start_hour: int = 9,
        work_end_hour: int = 18,
    ) -> List[dict]:
        """
        Suggest available time slots on a given date.

        Args:
            date: The date to check for availability
            duration_minutes: Desired meeting duration in minutes
            work_start_hour: Start of working hours (default 9)
            work_end_hour: End of working hours (default 18)

        Returns:
            List of available slot dicts with start_time and end_time
        """
        day_start = date.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)

        with ScheduleQueryUnitOfWork() as uow:
            existing = uow.repo.find_conflicts(day_start, day_end)

        # Sort by start_time
        busy = sorted(
            [(s.start_time, s.end_time) for s in existing],
            key=lambda x: x[0],
        )

        duration = timedelta(minutes=duration_minutes)
        available: List[dict] = []
        cursor = day_start

        for busy_start, busy_end in busy:
            if cursor + duration <= busy_start:
                available.append({
                    "start_time": cursor.isoformat(),
                    "end_time": (cursor + duration).isoformat(),
                })
            cursor = max(cursor, busy_end)

        # Check remaining time after last meeting
        if cursor + duration <= day_end:
            available.append({
                "start_time": cursor.isoformat(),
                "end_time": (cursor + duration).isoformat(),
            })

        return available

    def sync_schedule(self, user_id: str, schedule_id: str) -> ScheduleModel:
        """
        Manually sync a schedule to Google Calendar.

        Args:
            user_id: User attempting the sync
            schedule_id: The schedule UUID

        Returns:
            The synced schedule

        Raises:
            ScheduleNotFoundError: If schedule not found
            ScheduleAccessDeniedError: If user is not the creator
            GoogleCalendarNotConfiguredError: If Google Calendar not configured
            GoogleCalendarSyncError: If sync fails
        """
        with ScheduleUnitOfWork() as uow:
            schedule = uow.repo.get_by_id(schedule_id)
            if not schedule:
                raise ScheduleNotFoundError()

            if not schedule.can_edit(user_id):
                raise ScheduleAccessDeniedError()

            google_event_id = self._sync_to_google(uow, schedule, raise_on_error=True)
            if google_event_id:
                schedule.mark_synced(google_event_id)
                updated_schedule = uow.repo.update(schedule)
                uow.commit()
                return updated_schedule

            return schedule

    def _sync_to_google(
        self,
        uow: ScheduleUnitOfWork,
        schedule: ScheduleModel,
        raise_on_error: bool = False
    ) -> str | None:
        """
        Sync a schedule to Google Calendar.

        Args:
            uow: Unit of Work with Google config repo
            schedule: The schedule to sync
            raise_on_error: Whether to raise exceptions on error

        Returns:
            Google Calendar event ID if successful

        Raises:
            GoogleCalendarNotConfiguredError: If not configured and raise_on_error
            GoogleCalendarSyncError: If sync fails and raise_on_error
        """
        config = uow.google_config_repo.get_config()
        if not config:
            if raise_on_error:
                raise GoogleCalendarNotConfiguredError()
            return None

        # Import here to avoid circular imports
        from app.services.GoogleCalendarService import GoogleCalendarService

        try:
            calendar_service = GoogleCalendarService()

            # Check if token needs refresh
            # Ensure both datetimes are comparable (strip tzinfo from aware datetime)
            now_utc = datetime.utcnow()
            expires_at = config.expires_at.replace(tzinfo=None) if config.expires_at.tzinfo else config.expires_at
            if expires_at <= now_utc:
                logger.info("Google Calendar token expired, refreshing...")
                new_tokens = calendar_service.refresh_token(config.refresh_token)
                uow.google_config_repo.update_tokens(
                    access_token=new_tokens["access_token"],
                    expires_at=new_tokens["expires_at"].replace(tzinfo=None),
                    refresh_token=new_tokens.get("refresh_token")
                )
                config = uow.google_config_repo.get_config()

            # Create or update event
            if schedule.google_event_id:
                logger.info(f"Updating Google Calendar event: {schedule.google_event_id}")
                return calendar_service.update_event(
                    access_token=config.access_token,
                    calendar_id=config.calendar_id,
                    event_id=schedule.google_event_id,
                    schedule=schedule,
                )
            else:
                logger.info(f"Creating Google Calendar event for schedule: {schedule.title}")
                return calendar_service.create_event(
                    access_token=config.access_token,
                    calendar_id=config.calendar_id,
                    schedule=schedule,
                )

        except Exception as e:
            logger.error(f"Google Calendar sync failed: {e}")
            if raise_on_error:
                raise GoogleCalendarSyncError(message=str(e))
            return None

    def _delete_from_google(self, uow: ScheduleUnitOfWork, event_id: str) -> bool:
        """
        Delete an event from Google Calendar.

        Args:
            uow: Unit of Work with Google config repo
            event_id: Google Calendar event ID

        Returns:
            True if successful
        """
        config = uow.google_config_repo.get_config()
        if not config:
            return False

        from app.services.GoogleCalendarService import GoogleCalendarService

        try:
            calendar_service = GoogleCalendarService()

            # Check if token needs refresh
            now_utc = datetime.utcnow()
            expires_at = config.expires_at.replace(tzinfo=None) if config.expires_at.tzinfo else config.expires_at
            if expires_at <= now_utc:
                logger.info("Google Calendar token expired, refreshing...")
                new_tokens = calendar_service.refresh_token(config.refresh_token)
                uow.google_config_repo.update_tokens(
                    access_token=new_tokens["access_token"],
                    expires_at=new_tokens["expires_at"].replace(tzinfo=None),
                    refresh_token=new_tokens.get("refresh_token")
                )
                config = uow.google_config_repo.get_config()

            calendar_service.delete_event(
                access_token=config.access_token,
                calendar_id=config.calendar_id,
                event_id=event_id,
            )
            return True

        except Exception as e:
            logger.error(f"Google Calendar delete failed: {e}")
            return False

    def get_google_status(self) -> dict:
        """
        Get Google Calendar connection status.

        Returns:
            Dict with connection status info
        """
        with ScheduleQueryUnitOfWork() as uow:
            config = uow.google_config_repo.get_config()
            if not config:
                return {
                    "connected": False,
                    "calendar_id": None,
                    "expires_at": None,
                }
            return {
                "connected": True,
                "calendar_id": config.calendar_id,
                "expires_at": config.expires_at,
            }

    def connect_google(
        self,
        calendar_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime
    ) -> dict:
        """
        Connect Google Calendar.

        Args:
            calendar_id: Google Calendar ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: Token expiration time

        Returns:
            Dict with connection status
        """
        with ScheduleUnitOfWork() as uow:
            uow.google_config_repo.save_config(
                calendar_id=calendar_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
            uow.commit()
            return {
                "connected": True,
                "calendar_id": calendar_id,
            }

    def disconnect_google(self) -> dict:
        """
        Disconnect Google Calendar.

        Returns:
            Dict with disconnection status
        """
        with ScheduleUnitOfWork() as uow:
            uow.google_config_repo.delete_config()
            uow.commit()
            return {"connected": False}
