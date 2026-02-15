from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from .BaseRepository import BaseRepository
from database.models.schedule import Schedule, GoogleCalendarConfig
from app.domain.ScheduleModel import ScheduleModel, ScheduleCreator, TimeRange, GoogleSyncInfo


class ScheduleRepository(BaseRepository):
    """Repository for Schedule aggregate persistence operations."""

    def add(self, schedule_model: ScheduleModel) -> ScheduleModel:
        """
        Add a new schedule to the database.

        Args:
            schedule_model: The schedule domain model

        Returns:
            The created schedule with ID
        """
        schedule_entity = Schedule(
            id=UUID(schedule_model.id),
            title=schedule_model.title,
            description=schedule_model.description,
            location=schedule_model.location,
            start_time=schedule_model.start_time,
            end_time=schedule_model.end_time,
            all_day=schedule_model.all_day,
            timezone=schedule_model.timezone,
            creator_id=UUID(schedule_model.creator_id),
            google_event_id=schedule_model.google_event_id,
            synced_at=schedule_model.synced_at,
        )

        self.db.add(schedule_entity)
        self.db.flush()
        self.db.refresh(schedule_entity)

        return self._to_domain_model(schedule_entity)

    def get_by_id(self, schedule_id: str) -> Optional[ScheduleModel]:
        """
        Get a schedule by ID.

        Args:
            schedule_id: The schedule UUID

        Returns:
            ScheduleModel if found, None otherwise
        """
        schedule_entity = self.db.query(Schedule).filter(
            Schedule.id == UUID(schedule_id)
        ).first()

        if not schedule_entity:
            return None

        return self._to_domain_model(schedule_entity)

    def get_all(
        self,
        page: int,
        size: int,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
    ) -> Tuple[List[ScheduleModel], int]:
        """
        Get all schedules (paginated).

        Args:
            page: Page number
            size: Page size
            start_from: Filter schedules starting from this time
            start_to: Filter schedules starting before this time

        Returns:
            (list of schedules, total count)
        """
        query = self.db.query(Schedule)

        if start_from:
            query = query.filter(Schedule.start_time >= start_from)
        if start_to:
            query = query.filter(Schedule.start_time <= start_to)

        total = query.count()
        schedules = query.order_by(
            Schedule.start_time.asc()
        ).offset((page - 1) * size).limit(size).all()

        return [self._to_domain_model(s) for s in schedules], total

    def get_by_creator(
        self,
        creator_id: str,
        page: int,
        size: int
    ) -> Tuple[List[ScheduleModel], int]:
        """
        Get schedules by creator (paginated).

        Args:
            creator_id: Creator's UUID
            page: Page number
            size: Page size

        Returns:
            (list of schedules, total count)
        """
        query = self.db.query(Schedule).filter(
            Schedule.creator_id == UUID(creator_id)
        )

        total = query.count()
        schedules = query.order_by(
            Schedule.start_time.asc()
        ).offset((page - 1) * size).limit(size).all()

        return [self._to_domain_model(s) for s in schedules], total

    def update(self, schedule_model: ScheduleModel) -> ScheduleModel:
        """
        Update an existing schedule.

        Args:
            schedule_model: The updated schedule domain model

        Returns:
            The updated schedule
        """
        schedule_entity = self.db.query(Schedule).filter(
            Schedule.id == UUID(schedule_model.id)
        ).first()

        if not schedule_entity:
            raise ValueError(f"Schedule with ID {schedule_model.id} not found")

        schedule_entity.title = schedule_model.title
        schedule_entity.description = schedule_model.description
        schedule_entity.location = schedule_model.location
        schedule_entity.start_time = schedule_model.start_time
        schedule_entity.end_time = schedule_model.end_time
        schedule_entity.all_day = schedule_model.all_day
        schedule_entity.timezone = schedule_model.timezone
        schedule_entity.google_event_id = schedule_model.google_event_id
        schedule_entity.synced_at = schedule_model.synced_at

        self.db.flush()
        self.db.refresh(schedule_entity)

        return self._to_domain_model(schedule_entity)

    def delete(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: The schedule UUID

        Returns:
            True if deleted successfully
        """
        schedule_entity = self.db.query(Schedule).filter(
            Schedule.id == UUID(schedule_id)
        ).first()

        if not schedule_entity:
            return False

        self.db.delete(schedule_entity)
        self.db.flush()
        return True

    def find_conflicts(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_id: str | None = None,
    ) -> List[ScheduleModel]:
        """
        Find schedules that overlap with the given time range.

        Two events conflict when: existing.start < new.end AND existing.end > new.start

        Args:
            start_time: Start of the time range to check
            end_time: End of the time range to check
            exclude_id: Optional schedule ID to exclude (for update scenarios)

        Returns:
            List of conflicting schedules
        """
        query = self.db.query(Schedule).filter(
            Schedule.start_time < end_time,
            Schedule.end_time > start_time,
        )
        if exclude_id:
            query = query.filter(Schedule.id != UUID(exclude_id))

        conflicts = query.order_by(Schedule.start_time.asc()).all()
        return [self._to_domain_model(s) for s in conflicts]

    def _to_domain_model(self, entity: Schedule) -> ScheduleModel:
        """
        Convert a Schedule ORM entity to a ScheduleModel domain object.

        Args:
            entity: The Schedule ORM entity

        Returns:
            A ScheduleModel domain object
        """
        creator = None
        if entity.creator:
            creator = ScheduleCreator(
                user_id=str(entity.creator.id),
                username=entity.creator.uid,
                email=entity.creator.email
            )

        return ScheduleModel.reconstitute(
            id=str(entity.id),
            title=entity.title,
            description=entity.description,
            location=entity.location,
            start_time=entity.start_time,
            end_time=entity.end_time,
            all_day=entity.all_day,
            timezone=entity.timezone,
            creator_id=str(entity.creator_id),
            google_event_id=entity.google_event_id,
            synced_at=entity.synced_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            creator=creator,
        )


class GoogleCalendarConfigRepository(BaseRepository):
    """Repository for Google Calendar configuration."""

    def get_config(self) -> Optional[GoogleCalendarConfig]:
        """Get the Google Calendar configuration."""
        return self.db.query(GoogleCalendarConfig).first()

    def save_config(
        self,
        calendar_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime
    ) -> GoogleCalendarConfig:
        """
        Save or update Google Calendar configuration.

        Args:
            calendar_id: The Google Calendar ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_at: Token expiration time

        Returns:
            The saved configuration
        """
        config = self.db.query(GoogleCalendarConfig).first()

        if config:
            config.calendar_id = calendar_id
            config.access_token = access_token
            config.refresh_token = refresh_token
            config.expires_at = expires_at
        else:
            config = GoogleCalendarConfig(
                calendar_id=calendar_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
            self.db.add(config)

        self.db.flush()
        self.db.refresh(config)
        return config

    def update_tokens(
        self,
        access_token: str,
        expires_at: datetime,
        refresh_token: str | None = None
    ) -> bool:
        """
        Update OAuth tokens.

        Args:
            access_token: New access token
            expires_at: New expiration time
            refresh_token: New refresh token (optional)

        Returns:
            True if updated successfully
        """
        config = self.db.query(GoogleCalendarConfig).first()
        if not config:
            return False

        config.access_token = access_token
        config.expires_at = expires_at
        if refresh_token:
            config.refresh_token = refresh_token

        self.db.flush()
        return True

    def delete_config(self) -> bool:
        """Delete the Google Calendar configuration."""
        config = self.db.query(GoogleCalendarConfig).first()
        if not config:
            return False

        self.db.delete(config)
        self.db.flush()
        return True
