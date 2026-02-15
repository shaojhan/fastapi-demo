"""
Unit tests for ScheduleRepository.
Tests the data access layer for Schedule aggregates.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.ScheduleRepository import (
    ScheduleRepository,
    GoogleCalendarConfigRepository
)
from app.domain.ScheduleModel import ScheduleModel
from database.models.schedule import Schedule, GoogleCalendarConfig


class TestScheduleRepository:
    """Test suite for ScheduleRepository CRUD operations."""

    def test_add_schedule(self, test_db_session: Session, sample_users):
        """Test adding a new schedule."""
        repo = ScheduleRepository(test_db_session)
        creator = sample_users[0]

        # Create schedule using domain factory
        schedule = ScheduleModel.create(
            title="New Meeting",
            start_time=datetime(2024, 12, 5, 10, 0),
            end_time=datetime(2024, 12, 5, 11, 0),
            creator_id=str(creator.id),
            description="Test meeting",
            location="Room 101",
        )

        # Add to repository
        created_schedule = repo.add(schedule)

        # Verify
        assert created_schedule.id is not None
        assert created_schedule.title == "New Meeting"
        assert created_schedule.description == "Test meeting"
        assert created_schedule.location == "Room 101"
        assert created_schedule.creator_id == str(creator.id)
        assert created_schedule.created_at is not None

    def test_add_all_day_schedule(self, test_db_session: Session, sample_users):
        """Test adding an all-day schedule."""
        repo = ScheduleRepository(test_db_session)
        creator = sample_users[0]

        schedule = ScheduleModel.create(
            title="All Day Event",
            start_time=datetime(2024, 12, 25, 0, 0),
            end_time=datetime(2024, 12, 25, 23, 59),
            creator_id=str(creator.id),
            all_day=True,
        )

        created_schedule = repo.add(schedule)

        assert created_schedule.all_day is True

    def test_get_by_id_existing(self, test_db_session: Session, sample_schedules):
        """Test retrieving a schedule by ID."""
        repo = ScheduleRepository(test_db_session)
        existing_schedule = sample_schedules[0]

        # Retrieve by ID
        retrieved = repo.get_by_id(str(existing_schedule.id))

        # Verify
        assert retrieved is not None
        assert retrieved.id == str(existing_schedule.id)
        assert retrieved.title == "Team Meeting"
        assert retrieved.creator is not None
        assert retrieved.creator.username == "user1"

    def test_get_by_id_non_existing(self, test_db_session: Session):
        """Test retrieving a non-existing schedule by ID."""
        repo = ScheduleRepository(test_db_session)

        retrieved = repo.get_by_id(str(uuid4()))

        assert retrieved is None

    def test_get_all_paginated(self, test_db_session: Session, sample_schedules):
        """Test retrieving all schedules with pagination."""
        repo = ScheduleRepository(test_db_session)

        # Get first page
        schedules, total = repo.get_all(page=1, size=10)

        assert len(schedules) == 2
        assert total == 2
        # Sorted by start_time ascending
        assert schedules[0].title == "Team Meeting"
        assert schedules[1].title == "Project Review"

    def test_get_all_with_time_filter(self, test_db_session: Session, sample_schedules):
        """Test retrieving schedules with time filters."""
        repo = ScheduleRepository(test_db_session)

        # Filter for only December 1st
        schedules, total = repo.get_all(
            page=1,
            size=10,
            start_from=datetime(2024, 12, 1, 0, 0),
            start_to=datetime(2024, 12, 1, 23, 59)
        )

        assert len(schedules) == 1
        assert total == 1
        assert schedules[0].title == "Team Meeting"

    def test_get_all_empty(self, test_db_session: Session, sample_users):
        """Test retrieving schedules when none exist."""
        repo = ScheduleRepository(test_db_session)

        # Filter to a time range with no schedules
        schedules, total = repo.get_all(
            page=1,
            size=10,
            start_from=datetime(2025, 1, 1),
            start_to=datetime(2025, 1, 31)
        )

        assert len(schedules) == 0
        assert total == 0

    def test_get_by_creator(self, test_db_session: Session, sample_users, sample_schedules):
        """Test retrieving schedules by creator."""
        repo = ScheduleRepository(test_db_session)
        creator = sample_users[0]

        schedules, total = repo.get_by_creator(str(creator.id), page=1, size=10)

        assert len(schedules) == 2
        assert total == 2
        for schedule in schedules:
            assert schedule.creator_id == str(creator.id)

    def test_get_by_creator_no_schedules(self, test_db_session: Session, sample_users):
        """Test retrieving schedules by creator with no schedules."""
        repo = ScheduleRepository(test_db_session)
        user_without_schedules = sample_users[1]

        schedules, total = repo.get_by_creator(str(user_without_schedules.id), page=1, size=10)

        assert len(schedules) == 0
        assert total == 0

    def test_update_schedule(self, test_db_session: Session, sample_schedules):
        """Test updating a schedule."""
        repo = ScheduleRepository(test_db_session)
        existing = sample_schedules[0]

        # Get the schedule as domain model
        schedule = repo.get_by_id(str(existing.id))

        # Update fields
        schedule.update(
            title="Updated Team Meeting",
            description="Updated description",
            location="New Location"
        )

        # Save update
        updated = repo.update(schedule)

        # Verify
        assert updated.title == "Updated Team Meeting"
        assert updated.description == "Updated description"
        assert updated.location == "New Location"
        assert updated.updated_at is not None

    def test_update_schedule_time(self, test_db_session: Session, sample_schedules):
        """Test updating schedule time."""
        repo = ScheduleRepository(test_db_session)
        existing = sample_schedules[0]

        schedule = repo.get_by_id(str(existing.id))
        new_start = datetime(2024, 12, 10, 14, 0)
        new_end = datetime(2024, 12, 10, 15, 0)

        schedule.update(start_time=new_start, end_time=new_end)
        updated = repo.update(schedule)

        assert updated.start_time == new_start
        assert updated.end_time == new_end

    def test_update_non_existing_schedule(self, test_db_session: Session, sample_users):
        """Test updating a non-existing schedule raises error."""
        repo = ScheduleRepository(test_db_session)

        # Create a schedule with fake ID
        schedule = ScheduleModel.reconstitute(
            id=str(uuid4()),
            title="Fake",
            description=None,
            location=None,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
            all_day=False,
            timezone="Asia/Taipei",
            creator_id=str(sample_users[0].id),
            google_event_id=None,
            synced_at=None,
            created_at=datetime.now(),
            updated_at=None,
            creator=None
        )

        with pytest.raises(ValueError, match="not found"):
            repo.update(schedule)

    def test_delete_existing_schedule(self, test_db_session: Session, sample_schedules):
        """Test deleting an existing schedule."""
        repo = ScheduleRepository(test_db_session)
        schedule_to_delete = sample_schedules[0]

        result = repo.delete(str(schedule_to_delete.id))

        assert result is True
        assert repo.get_by_id(str(schedule_to_delete.id)) is None

    def test_delete_non_existing_schedule(self, test_db_session: Session):
        """Test deleting a non-existing schedule."""
        repo = ScheduleRepository(test_db_session)

        result = repo.delete(str(uuid4()))

        assert result is False

    def test_schedule_with_google_sync_info(self, test_db_session: Session, sample_users):
        """Test schedule with Google Calendar sync info."""
        repo = ScheduleRepository(test_db_session)
        creator = sample_users[0]

        schedule = ScheduleModel.create(
            title="Synced Meeting",
            start_time=datetime(2024, 12, 15, 10, 0),
            end_time=datetime(2024, 12, 15, 11, 0),
            creator_id=str(creator.id),
        )

        created = repo.add(schedule)

        # Mark as synced
        created.mark_synced("google_event_123")
        updated = repo.update(created)

        assert updated.google_event_id == "google_event_123"
        assert updated.synced_at is not None

    def test_domain_model_preserves_creator_info(self, test_db_session: Session, sample_schedules):
        """Test that converting to domain model preserves creator info."""
        repo = ScheduleRepository(test_db_session)
        existing = sample_schedules[0]

        schedule = repo.get_by_id(str(existing.id))

        assert schedule.creator is not None
        assert schedule.creator.user_id == str(existing.creator_id)
        assert schedule.creator.username == "user1"
        assert schedule.creator.email == "user1@example.com"


class TestScheduleRepositoryFindConflicts:
    """Test suite for ScheduleRepository.find_conflicts."""

    def test_find_conflicts_overlapping(self, test_db_session: Session, sample_schedules):
        """Test finding conflicts with overlapping time range."""
        repo = ScheduleRepository(test_db_session)
        # sample_schedules[0]: 2024-12-01 09:00-10:00
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 9, 30),
            end_time=datetime(2024, 12, 1, 10, 30),
        )
        assert len(conflicts) == 1
        assert conflicts[0].title == "Team Meeting"

    def test_find_conflicts_no_overlap(self, test_db_session: Session, sample_schedules):
        """Test no conflicts when time ranges don't overlap."""
        repo = ScheduleRepository(test_db_session)
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 11, 0),
            end_time=datetime(2024, 12, 1, 12, 0),
        )
        assert len(conflicts) == 0

    def test_find_conflicts_exact_boundary_no_overlap(self, test_db_session: Session, sample_schedules):
        """Test that adjacent events (end == start) don't conflict."""
        repo = ScheduleRepository(test_db_session)
        # Ends exactly when Team Meeting starts
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 8, 0),
            end_time=datetime(2024, 12, 1, 9, 0),
        )
        assert len(conflicts) == 0

    def test_find_conflicts_containing(self, test_db_session: Session, sample_schedules):
        """Test conflict when new range fully contains existing."""
        repo = ScheduleRepository(test_db_session)
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 8, 0),
            end_time=datetime(2024, 12, 1, 11, 0),
        )
        assert len(conflicts) == 1
        assert conflicts[0].title == "Team Meeting"

    def test_find_conflicts_multiple(self, test_db_session: Session, sample_schedules):
        """Test finding multiple conflicts across a wide range."""
        repo = ScheduleRepository(test_db_session)
        # Spans both sample schedules
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 0, 0),
            end_time=datetime(2024, 12, 3, 0, 0),
        )
        assert len(conflicts) == 2

    def test_find_conflicts_with_exclude_id(self, test_db_session: Session, sample_schedules):
        """Test excluding a schedule by ID (update scenario)."""
        repo = ScheduleRepository(test_db_session)
        exclude = sample_schedules[0]
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 0, 0),
            end_time=datetime(2024, 12, 3, 0, 0),
            exclude_id=str(exclude.id),
        )
        assert len(conflicts) == 1
        assert conflicts[0].title == "Project Review"

    def test_find_conflicts_empty_db(self, test_db_session: Session, sample_users):
        """Test no conflicts when no schedules exist."""
        repo = ScheduleRepository(test_db_session)
        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 1, 9, 0),
            end_time=datetime(2024, 12, 1, 10, 0),
        )
        assert len(conflicts) == 0

    def test_find_conflicts_ordered_by_start_time(self, test_db_session: Session, sample_users):
        """Test results are ordered by start_time ascending."""
        repo = ScheduleRepository(test_db_session)
        creator = sample_users[0]

        # Create schedules in reverse order
        for hour in [15, 11, 13]:
            schedule = Schedule(
                id=uuid4(),
                title=f"Meeting at {hour}",
                start_time=datetime(2024, 12, 5, hour, 0),
                end_time=datetime(2024, 12, 5, hour + 1, 0),
                all_day=False,
                timezone="Asia/Taipei",
                creator_id=creator.id,
            )
            test_db_session.add(schedule)
        test_db_session.commit()

        conflicts = repo.find_conflicts(
            start_time=datetime(2024, 12, 5, 10, 0),
            end_time=datetime(2024, 12, 5, 16, 0),
        )
        assert len(conflicts) == 3
        assert conflicts[0].title == "Meeting at 11"
        assert conflicts[1].title == "Meeting at 13"
        assert conflicts[2].title == "Meeting at 15"


class TestGoogleCalendarConfigRepository:
    """Test suite for GoogleCalendarConfigRepository."""

    def test_get_config_not_exists(self, test_db_session: Session):
        """Test getting config when none exists."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        config = repo.get_config()

        assert config is None

    def test_save_config(self, test_db_session: Session):
        """Test saving Google Calendar config."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        expires_at = datetime.now() + timedelta(hours=1)
        saved_config = repo.save_config(
            calendar_id="company@group.calendar.google.com",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_at=expires_at
        )

        assert saved_config.id is not None
        assert saved_config.calendar_id == "company@group.calendar.google.com"
        assert saved_config.access_token == "access_token_123"
        assert saved_config.refresh_token == "refresh_token_456"

    def test_save_config_overwrites_existing(self, test_db_session: Session):
        """Test saving config overwrites existing."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        # Save initial config
        expires_at1 = datetime.now() + timedelta(hours=1)
        repo.save_config(
            calendar_id="old@calendar.google.com",
            access_token="old_token",
            refresh_token="old_refresh",
            expires_at=expires_at1
        )
        test_db_session.commit()

        # Save new config
        expires_at2 = datetime.now() + timedelta(hours=2)
        updated = repo.save_config(
            calendar_id="new@calendar.google.com",
            access_token="new_token",
            refresh_token="new_refresh",
            expires_at=expires_at2
        )

        # Verify only one config exists with new values
        all_configs = test_db_session.query(GoogleCalendarConfig).all()
        assert len(all_configs) == 1
        assert all_configs[0].calendar_id == "new@calendar.google.com"

    def test_update_tokens(self, test_db_session: Session):
        """Test updating OAuth tokens."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        # Save initial config
        expires_at = datetime.now() + timedelta(hours=1)
        repo.save_config(
            calendar_id="company@calendar.google.com",
            access_token="old_access",
            refresh_token="old_refresh",
            expires_at=expires_at
        )
        test_db_session.commit()

        # Update tokens
        new_expires = datetime.now() + timedelta(hours=2)
        result = repo.update_tokens(
            access_token="new_access",
            expires_at=new_expires
        )

        assert result is True
        config = repo.get_config()
        assert config.access_token == "new_access"
        assert config.refresh_token == "old_refresh"  # Not updated

    def test_update_tokens_with_refresh(self, test_db_session: Session):
        """Test updating OAuth tokens including refresh token."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        # Save initial config
        expires_at = datetime.now() + timedelta(hours=1)
        repo.save_config(
            calendar_id="company@calendar.google.com",
            access_token="old_access",
            refresh_token="old_refresh",
            expires_at=expires_at
        )
        test_db_session.commit()

        # Update tokens including refresh
        new_expires = datetime.now() + timedelta(hours=2)
        result = repo.update_tokens(
            access_token="new_access",
            expires_at=new_expires,
            refresh_token="new_refresh"
        )

        assert result is True
        config = repo.get_config()
        assert config.access_token == "new_access"
        assert config.refresh_token == "new_refresh"

    def test_update_tokens_no_config(self, test_db_session: Session):
        """Test updating tokens when no config exists."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        result = repo.update_tokens(
            access_token="token",
            expires_at=datetime.now()
        )

        assert result is False

    def test_delete_config(self, test_db_session: Session):
        """Test deleting Google Calendar config."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        # Save config
        expires_at = datetime.now() + timedelta(hours=1)
        repo.save_config(
            calendar_id="company@calendar.google.com",
            access_token="access",
            refresh_token="refresh",
            expires_at=expires_at
        )
        test_db_session.commit()

        # Delete config
        result = repo.delete_config()

        assert result is True
        assert repo.get_config() is None

    def test_delete_config_not_exists(self, test_db_session: Session):
        """Test deleting config when none exists."""
        repo = GoogleCalendarConfigRepository(test_db_session)

        result = repo.delete_config()

        assert result is False
