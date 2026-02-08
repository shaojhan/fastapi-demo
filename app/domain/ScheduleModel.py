from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class TimeRange:
    """
    Value Object representing a schedule time range.
    """
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "Asia/Taipei"

    def __post_init__(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")


@dataclass(frozen=True)
class GoogleSyncInfo:
    """
    Value Object representing Google Calendar sync state.
    """
    event_id: str | None = None
    synced_at: datetime | None = None

    @property
    def is_synced(self) -> bool:
        return self.event_id is not None


@dataclass(frozen=True)
class ScheduleCreator:
    """
    Value Object representing a schedule creator's info.
    """
    user_id: str
    username: str
    email: str


class ScheduleModel:
    """
    Aggregate Root representing a schedule in the domain.
    Use factory methods `create` or `reconstitute` to create instances.
    """

    def __init__(
        self,
        id: str,
        title: str,
        time_range: TimeRange,
        creator_id: str,
        description: str | None = None,
        location: str | None = None,
        google_sync: GoogleSyncInfo | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        creator: ScheduleCreator | None = None,
    ):
        self._id = id
        self._title = title
        self._description = description
        self._location = location
        self._time_range = time_range
        self._creator_id = creator_id
        self._google_sync = google_sync or GoogleSyncInfo()
        self._created_at = created_at
        self._updated_at = updated_at
        self._creator = creator

    # Properties
    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def location(self) -> str | None:
        return self._location

    @property
    def time_range(self) -> TimeRange:
        return self._time_range

    @property
    def start_time(self) -> datetime:
        return self._time_range.start_time

    @property
    def end_time(self) -> datetime:
        return self._time_range.end_time

    @property
    def all_day(self) -> bool:
        return self._time_range.all_day

    @property
    def timezone(self) -> str:
        return self._time_range.timezone

    @property
    def creator_id(self) -> str:
        return self._creator_id

    @property
    def google_sync(self) -> GoogleSyncInfo:
        return self._google_sync

    @property
    def google_event_id(self) -> str | None:
        return self._google_sync.event_id

    @property
    def synced_at(self) -> datetime | None:
        return self._google_sync.synced_at

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def creator(self) -> ScheduleCreator | None:
        return self._creator

    # Factory methods
    @staticmethod
    def create(
        title: str,
        start_time: datetime,
        end_time: datetime,
        creator_id: str,
        description: str | None = None,
        location: str | None = None,
        all_day: bool = False,
        timezone: str = "Asia/Taipei",
    ) -> "ScheduleModel":
        """
        Factory method to create a new schedule.

        Args:
            title: Schedule title
            start_time: Start time
            end_time: End time
            creator_id: Creator's UUID
            description: Optional description
            location: Optional location
            all_day: Whether this is an all-day event
            timezone: Timezone string

        Returns:
            A new ScheduleModel instance

        Raises:
            ValueError: If title is empty or time range is invalid
        """
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")

        time_range = TimeRange(
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            timezone=timezone,
        )

        return ScheduleModel(
            id=str(uuid4()),
            title=title.strip(),
            description=description.strip() if description else None,
            location=location.strip() if location else None,
            time_range=time_range,
            creator_id=creator_id,
            google_sync=GoogleSyncInfo(),
            created_at=datetime.utcnow(),
            updated_at=None,
        )

    @staticmethod
    def reconstitute(
        id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        creator_id: str,
        description: str | None,
        location: str | None,
        all_day: bool,
        timezone: str,
        google_event_id: str | None,
        synced_at: datetime | None,
        created_at: datetime | None,
        updated_at: datetime | None,
        creator: ScheduleCreator | None = None,
    ) -> "ScheduleModel":
        """
        Factory method to reconstitute a schedule from persistence.

        Returns:
            A reconstituted ScheduleModel instance
        """
        time_range = TimeRange(
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            timezone=timezone,
        )

        google_sync = GoogleSyncInfo(
            event_id=google_event_id,
            synced_at=synced_at,
        )

        return ScheduleModel(
            id=id,
            title=title,
            description=description,
            location=location,
            time_range=time_range,
            creator_id=creator_id,
            google_sync=google_sync,
            created_at=created_at,
            updated_at=updated_at,
            creator=creator,
        )

    # Business methods
    def can_edit(self, user_id: str) -> bool:
        """
        Check if a user can edit this schedule.
        Only the creator can edit.

        Args:
            user_id: The user ID to check

        Returns:
            True if the user can edit
        """
        return user_id == self._creator_id

    def update(
        self,
        title: str | None = None,
        description: str | None = None,
        location: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        all_day: bool | None = None,
        timezone: str | None = None,
    ) -> None:
        """
        Update schedule fields.

        Args:
            title: New title (optional)
            description: New description (optional)
            location: New location (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            all_day: New all_day flag (optional)
            timezone: New timezone (optional)
        """
        if title is not None:
            if not title.strip():
                raise ValueError("Title cannot be empty")
            self._title = title.strip()

        if description is not None:
            self._description = description.strip() if description else None

        if location is not None:
            self._location = location.strip() if location else None

        # Update time range if any time field changed
        new_start = start_time if start_time is not None else self._time_range.start_time
        new_end = end_time if end_time is not None else self._time_range.end_time
        new_all_day = all_day if all_day is not None else self._time_range.all_day
        new_tz = timezone if timezone is not None else self._time_range.timezone

        if start_time is not None or end_time is not None or all_day is not None or timezone is not None:
            self._time_range = TimeRange(
                start_time=new_start,
                end_time=new_end,
                all_day=new_all_day,
                timezone=new_tz,
            )

        self._updated_at = datetime.utcnow()

    def mark_synced(self, google_event_id: str) -> None:
        """
        Mark this schedule as synced to Google Calendar.

        Args:
            google_event_id: The Google Calendar event ID
        """
        self._google_sync = GoogleSyncInfo(
            event_id=google_event_id,
            synced_at=datetime.utcnow(),
        )
        self._updated_at = datetime.utcnow()

    def clear_sync(self) -> None:
        """Clear Google Calendar sync info (after deletion from Google)."""
        self._google_sync = GoogleSyncInfo()
        self._updated_at = datetime.utcnow()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScheduleModel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
