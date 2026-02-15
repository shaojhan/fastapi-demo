"""
Unit tests for ScheduleService.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.ScheduleService import ScheduleService
from app.domain.ScheduleModel import ScheduleModel, ScheduleCreator
from app.exceptions.ScheduleException import (
    ScheduleNotFoundError,
    ScheduleAccessDeniedError,
    GoogleCalendarNotConfiguredError,
    GoogleCalendarSyncError,
)


# --- Test Data ---
TEST_USER_ID = str(uuid4())
TEST_SCHEDULE_ID = str(uuid4())
TEST_TITLE = "Team Meeting"
TEST_START_TIME = datetime(2024, 12, 1, 9, 0)
TEST_END_TIME = datetime(2024, 12, 1, 10, 0)


def _make_schedule_model(
    schedule_id=None,
    creator_id=None,
    title=TEST_TITLE,
    start_time=TEST_START_TIME,
    end_time=TEST_END_TIME,
    google_event_id=None,
) -> ScheduleModel:
    """Create a test ScheduleModel."""
    return ScheduleModel.reconstitute(
        id=schedule_id or TEST_SCHEDULE_ID,
        title=title,
        description="Test description",
        location="Meeting Room A",
        start_time=start_time,
        end_time=end_time,
        all_day=False,
        timezone="Asia/Taipei",
        creator_id=creator_id or TEST_USER_ID,
        google_event_id=google_event_id,
        synced_at=None,
        created_at=datetime.now(),
        updated_at=None,
        creator=ScheduleCreator(
            user_id=creator_id or TEST_USER_ID,
            username="testuser",
            email="test@example.com"
        )
    )


class TestCreateSchedule:
    """Tests for ScheduleService.create_schedule"""

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_create_schedule_success(self, mock_uow_class):
        """Test creating a schedule successfully."""
        # Arrange
        created_schedule = _make_schedule_model()

        mock_repo = MagicMock()
        mock_repo.add.return_value = created_schedule

        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.create_schedule(
            creator_id=TEST_USER_ID,
            title=TEST_TITLE,
            start_time=TEST_START_TIME,
            end_time=TEST_END_TIME,
            description="Test description",
            location="Meeting Room A",
        )

        # Assert
        mock_repo.add.assert_called_once()
        mock_uow.commit.assert_called_once()
        assert result.title == TEST_TITLE

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_create_schedule_with_all_day_event(self, mock_uow_class):
        """Test creating an all-day schedule."""
        # Arrange
        created_schedule = _make_schedule_model()

        mock_repo = MagicMock()
        mock_repo.add.return_value = created_schedule

        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.create_schedule(
            creator_id=TEST_USER_ID,
            title=TEST_TITLE,
            start_time=TEST_START_TIME,
            end_time=TEST_END_TIME,
            all_day=True,
        )

        # Assert
        mock_repo.add.assert_called_once()
        add_call_args = mock_repo.add.call_args[0][0]
        assert add_call_args.all_day is True


class TestGetSchedule:
    """Tests for ScheduleService.get_schedule"""

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_get_schedule_success(self, mock_uow_class):
        """Test getting a schedule by ID."""
        # Arrange
        schedule = _make_schedule_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.get_schedule(TEST_SCHEDULE_ID)

        # Assert
        mock_repo.get_by_id.assert_called_once_with(TEST_SCHEDULE_ID)
        assert result.id == TEST_SCHEDULE_ID
        assert result.title == TEST_TITLE

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_get_schedule_not_found(self, mock_uow_class):
        """Test getting a non-existent schedule raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleNotFoundError):
            service.get_schedule(str(uuid4()))


class TestListSchedules:
    """Tests for ScheduleService.list_schedules"""

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_list_schedules_success(self, mock_uow_class):
        """Test listing schedules with pagination."""
        # Arrange
        schedules = [
            _make_schedule_model(schedule_id=str(uuid4()), title="Meeting 1"),
            _make_schedule_model(schedule_id=str(uuid4()), title="Meeting 2"),
        ]

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = (schedules, 2)

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result, total = service.list_schedules(page=1, size=20)

        # Assert
        mock_repo.get_all.assert_called_once_with(1, 20, None, None)
        assert len(result) == 2
        assert total == 2

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_list_schedules_with_time_filter(self, mock_uow_class):
        """Test listing schedules with time filters."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_all.return_value = ([], 0)

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        start_from = datetime(2024, 1, 1)
        start_to = datetime(2024, 12, 31)

        # Act
        service = ScheduleService()
        service.list_schedules(page=1, size=10, start_from=start_from, start_to=start_to)

        # Assert
        mock_repo.get_all.assert_called_once_with(1, 10, start_from, start_to)


class TestUpdateSchedule:
    """Tests for ScheduleService.update_schedule"""

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_update_schedule_success(self, mock_uow_class):
        """Test updating a schedule successfully."""
        # Arrange
        schedule = _make_schedule_model()
        updated_schedule = _make_schedule_model(title="Updated Meeting")

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule
        mock_repo.update.return_value = updated_schedule

        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.update_schedule(
            user_id=TEST_USER_ID,
            schedule_id=TEST_SCHEDULE_ID,
            title="Updated Meeting",
        )

        # Assert
        mock_repo.get_by_id.assert_called_once_with(TEST_SCHEDULE_ID)
        mock_repo.update.assert_called_once()
        mock_uow.commit.assert_called_once()
        assert result.title == "Updated Meeting"

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_update_schedule_not_found(self, mock_uow_class):
        """Test updating non-existent schedule raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleNotFoundError):
            service.update_schedule(
                user_id=TEST_USER_ID,
                schedule_id=str(uuid4()),
                title="Updated",
            )

        mock_uow.commit.assert_not_called()

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_update_schedule_access_denied(self, mock_uow_class):
        """Test updating schedule by non-creator raises error."""
        # Arrange
        schedule = _make_schedule_model(creator_id=str(uuid4()))  # Different creator

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleAccessDeniedError):
            service.update_schedule(
                user_id=TEST_USER_ID,
                schedule_id=TEST_SCHEDULE_ID,
                title="Updated",
            )

        mock_repo.update.assert_not_called()
        mock_uow.commit.assert_not_called()


class TestDeleteSchedule:
    """Tests for ScheduleService.delete_schedule"""

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_delete_schedule_success(self, mock_uow_class):
        """Test deleting a schedule successfully."""
        # Arrange
        schedule = _make_schedule_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule
        mock_repo.delete.return_value = True

        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        service.delete_schedule(user_id=TEST_USER_ID, schedule_id=TEST_SCHEDULE_ID)

        # Assert
        mock_repo.get_by_id.assert_called_once_with(TEST_SCHEDULE_ID)
        mock_repo.delete.assert_called_once_with(TEST_SCHEDULE_ID)
        mock_uow.commit.assert_called_once()

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_delete_schedule_not_found(self, mock_uow_class):
        """Test deleting non-existent schedule raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleNotFoundError):
            service.delete_schedule(user_id=TEST_USER_ID, schedule_id=str(uuid4()))

        mock_uow.commit.assert_not_called()

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_delete_schedule_access_denied(self, mock_uow_class):
        """Test deleting schedule by non-creator raises error."""
        # Arrange
        schedule = _make_schedule_model(creator_id=str(uuid4()))  # Different creator

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleAccessDeniedError):
            service.delete_schedule(user_id=TEST_USER_ID, schedule_id=TEST_SCHEDULE_ID)

        mock_repo.delete.assert_not_called()
        mock_uow.commit.assert_not_called()


class TestSyncSchedule:
    """Tests for ScheduleService.sync_schedule"""

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_sync_schedule_not_found(self, mock_uow_class):
        """Test syncing non-existent schedule raises error."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleNotFoundError):
            service.sync_schedule(user_id=TEST_USER_ID, schedule_id=str(uuid4()))

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_sync_schedule_access_denied(self, mock_uow_class):
        """Test syncing schedule by non-creator raises error."""
        # Arrange
        schedule = _make_schedule_model(creator_id=str(uuid4()))  # Different creator

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(ScheduleAccessDeniedError):
            service.sync_schedule(user_id=TEST_USER_ID, schedule_id=TEST_SCHEDULE_ID)

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_sync_schedule_google_not_configured(self, mock_uow_class):
        """Test syncing schedule when Google Calendar is not configured."""
        # Arrange
        schedule = _make_schedule_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = schedule

        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = ScheduleService()
        with pytest.raises(GoogleCalendarNotConfiguredError):
            service.sync_schedule(user_id=TEST_USER_ID, schedule_id=TEST_SCHEDULE_ID)


class TestGetGoogleStatus:
    """Tests for ScheduleService.get_google_status"""

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_get_google_status_not_connected(self, mock_uow_class):
        """Test getting Google status when not connected."""
        # Arrange
        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = None

        mock_uow = MagicMock()
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.get_google_status()

        # Assert
        assert result["connected"] is False
        assert result["calendar_id"] is None

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_get_google_status_connected(self, mock_uow_class):
        """Test getting Google status when connected."""
        # Arrange
        mock_config = MagicMock()
        mock_config.calendar_id = "test@group.calendar.google.com"
        mock_config.expires_at = datetime.now() + timedelta(hours=1)

        mock_google_config_repo = MagicMock()
        mock_google_config_repo.get_config.return_value = mock_config

        mock_uow = MagicMock()
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.get_google_status()

        # Assert
        assert result["connected"] is True
        assert result["calendar_id"] == "test@group.calendar.google.com"


class TestCheckConflicts:
    """Tests for ScheduleService.check_conflicts"""

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_check_conflicts_found(self, mock_uow_class):
        """Test finding conflicts in a time range."""
        conflicts = [
            _make_schedule_model(schedule_id=str(uuid4()), title="Conflict 1"),
            _make_schedule_model(schedule_id=str(uuid4()), title="Conflict 2"),
        ]

        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = conflicts

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        result = service.check_conflicts(
            start_time=TEST_START_TIME,
            end_time=TEST_END_TIME,
        )

        assert len(result) == 2
        mock_repo.find_conflicts.assert_called_once_with(TEST_START_TIME, TEST_END_TIME, None)

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_check_conflicts_none(self, mock_uow_class):
        """Test no conflicts found."""
        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = []

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        result = service.check_conflicts(
            start_time=TEST_START_TIME,
            end_time=TEST_END_TIME,
        )

        assert len(result) == 0

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_check_conflicts_with_exclude_id(self, mock_uow_class):
        """Test checking conflicts with exclude_id for update scenario."""
        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = []

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        service.check_conflicts(
            start_time=TEST_START_TIME,
            end_time=TEST_END_TIME,
            exclude_id=TEST_SCHEDULE_ID,
        )

        mock_repo.find_conflicts.assert_called_once_with(TEST_START_TIME, TEST_END_TIME, TEST_SCHEDULE_ID)


class TestSuggestAvailableSlots:
    """Tests for ScheduleService.suggest_available_slots"""

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_suggest_slots_no_existing(self, mock_uow_class):
        """Test suggesting slots when no existing schedules."""
        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = []

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        date = datetime(2024, 12, 5, 0, 0)
        slots = service.suggest_available_slots(date, duration_minutes=60)

        # First available slot should start at work_start_hour
        assert len(slots) >= 1
        assert slots[0]["start_time"] == datetime(2024, 12, 5, 9, 0).isoformat()
        assert slots[0]["end_time"] == datetime(2024, 12, 5, 10, 0).isoformat()

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_suggest_slots_with_gap(self, mock_uow_class):
        """Test suggesting slots with a gap between existing schedules."""
        existing = [
            _make_schedule_model(
                start_time=datetime(2024, 12, 5, 9, 0),
                end_time=datetime(2024, 12, 5, 10, 0),
            ),
            _make_schedule_model(
                start_time=datetime(2024, 12, 5, 12, 0),
                end_time=datetime(2024, 12, 5, 13, 0),
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = existing

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        date = datetime(2024, 12, 5, 0, 0)
        slots = service.suggest_available_slots(date, duration_minutes=60)

        # Should have slot at 10:00, and after 13:00
        assert len(slots) >= 2
        assert slots[0]["start_time"] == datetime(2024, 12, 5, 10, 0).isoformat()

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_suggest_slots_fully_booked(self, mock_uow_class):
        """Test suggesting slots when day is fully booked."""
        # 9 hours of back-to-back meetings (9-18)
        existing = [
            _make_schedule_model(
                start_time=datetime(2024, 12, 5, 9, 0),
                end_time=datetime(2024, 12, 5, 18, 0),
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = existing

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        date = datetime(2024, 12, 5, 0, 0)
        slots = service.suggest_available_slots(date, duration_minutes=60)

        assert len(slots) == 0

    @patch("app.services.ScheduleService.ScheduleQueryUnitOfWork")
    def test_suggest_slots_custom_work_hours(self, mock_uow_class):
        """Test suggesting slots with custom work hours."""
        mock_repo = MagicMock()
        mock_repo.find_conflicts.return_value = []

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ScheduleService()
        date = datetime(2024, 12, 5, 0, 0)
        slots = service.suggest_available_slots(
            date, duration_minutes=60, work_start_hour=10, work_end_hour=14
        )

        assert len(slots) >= 1
        assert slots[0]["start_time"] == datetime(2024, 12, 5, 10, 0).isoformat()


class TestConnectGoogle:
    """Tests for ScheduleService.connect_google"""

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_connect_google_success(self, mock_uow_class):
        """Test connecting Google Calendar."""
        # Arrange
        mock_google_config_repo = MagicMock()

        mock_uow = MagicMock()
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        calendar_id = "test@group.calendar.google.com"
        access_token = "access_token_123"
        refresh_token = "refresh_token_456"
        expires_at = datetime.now() + timedelta(hours=1)

        # Act
        service = ScheduleService()
        result = service.connect_google(
            calendar_id=calendar_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

        # Assert
        mock_google_config_repo.save_config.assert_called_once_with(
            calendar_id=calendar_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        mock_uow.commit.assert_called_once()
        assert result["connected"] is True
        assert result["calendar_id"] == calendar_id


class TestDisconnectGoogle:
    """Tests for ScheduleService.disconnect_google"""

    @patch("app.services.ScheduleService.ScheduleUnitOfWork")
    def test_disconnect_google_success(self, mock_uow_class):
        """Test disconnecting Google Calendar."""
        # Arrange
        mock_google_config_repo = MagicMock()
        mock_google_config_repo.delete_config.return_value = True

        mock_uow = MagicMock()
        mock_uow.google_config_repo = mock_google_config_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = ScheduleService()
        result = service.disconnect_google()

        # Assert
        mock_google_config_repo.delete_config.assert_called_once()
        mock_uow.commit.assert_called_once()
        assert result["connected"] is False
