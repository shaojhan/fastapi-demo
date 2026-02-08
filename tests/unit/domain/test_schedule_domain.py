import pytest
from datetime import datetime, timedelta
from uuid import UUID
from app.domain.ScheduleModel import (
    ScheduleModel,
    TimeRange,
    GoogleSyncInfo,
    ScheduleCreator,
)


# --- Test Data ---
TEST_TITLE = "Team Meeting"
TEST_DESCRIPTION = "Weekly team sync meeting"
TEST_LOCATION = "Conference Room A"
TEST_CREATOR_ID = "11d200ac-48d8-4675-bfc0-a3a61af3c499"
TEST_TIMEZONE = "Asia/Taipei"


def get_valid_time_range() -> tuple[datetime, datetime]:
    """取得有效的時間範圍（開始時間在結束時間之前）"""
    start = datetime(2024, 1, 15, 9, 0, 0)
    end = datetime(2024, 1, 15, 10, 0, 0)
    return start, end


class TestTimeRange:
    """測試 TimeRange 值物件"""

    def test_time_range_creation_with_valid_data(self):
        """
        測試使用有效時間範圍建立 TimeRange。
        """
        start, end = get_valid_time_range()
        time_range = TimeRange(
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE
        )

        assert time_range.start_time == start
        assert time_range.end_time == end
        assert time_range.all_day is False
        assert time_range.timezone == TEST_TIMEZONE

    def test_time_range_creation_with_default_values(self):
        """
        測試 TimeRange 的預設值。
        """
        start, end = get_valid_time_range()
        time_range = TimeRange(start_time=start, end_time=end)

        assert time_range.all_day is False
        assert time_range.timezone == "Asia/Taipei"

    def test_time_range_with_invalid_range_raises_error(self):
        """
        測試開始時間在結束時間之後會拋出 ValueError。
        """
        start = datetime(2024, 1, 15, 10, 0, 0)
        end = datetime(2024, 1, 15, 9, 0, 0)  # 結束時間早於開始時間

        with pytest.raises(ValueError, match="Start time must be before end time"):
            TimeRange(start_time=start, end_time=end)

    def test_time_range_with_equal_times_raises_error(self):
        """
        測試開始時間等於結束時間會拋出 ValueError。
        """
        same_time = datetime(2024, 1, 15, 9, 0, 0)

        with pytest.raises(ValueError, match="Start time must be before end time"):
            TimeRange(start_time=same_time, end_time=same_time)

    def test_time_range_all_day_event(self):
        """
        測試全天事件。
        """
        start = datetime(2024, 1, 15, 0, 0, 0)
        end = datetime(2024, 1, 16, 0, 0, 0)
        time_range = TimeRange(
            start_time=start,
            end_time=end,
            all_day=True
        )

        assert time_range.all_day is True

    def test_time_range_immutability(self):
        """
        測試 TimeRange 是不可變的（frozen dataclass）。
        """
        start, end = get_valid_time_range()
        time_range = TimeRange(start_time=start, end_time=end)

        with pytest.raises(Exception):  # FrozenInstanceError
            time_range.start_time = datetime.now()

    def test_time_range_equality(self):
        """
        測試 TimeRange 的相等性比較。
        """
        start, end = get_valid_time_range()
        range1 = TimeRange(start_time=start, end_time=end, timezone="Asia/Taipei")
        range2 = TimeRange(start_time=start, end_time=end, timezone="Asia/Taipei")
        range3 = TimeRange(start_time=start, end_time=end, timezone="UTC")

        assert range1 == range2
        assert range1 != range3


class TestGoogleSyncInfo:
    """測試 GoogleSyncInfo 值物件"""

    def test_google_sync_info_default_values(self):
        """
        測試 GoogleSyncInfo 的預設值。
        """
        sync_info = GoogleSyncInfo()

        assert sync_info.event_id is None
        assert sync_info.synced_at is None
        assert sync_info.is_synced is False

    def test_google_sync_info_with_event_id(self):
        """
        測試有 event_id 的 GoogleSyncInfo。
        """
        now = datetime.utcnow()
        sync_info = GoogleSyncInfo(
            event_id="google_event_123",
            synced_at=now
        )

        assert sync_info.event_id == "google_event_123"
        assert sync_info.synced_at == now
        assert sync_info.is_synced is True

    def test_google_sync_info_is_synced_property(self):
        """
        測試 is_synced 屬性正確反映同步狀態。
        """
        not_synced = GoogleSyncInfo()
        synced = GoogleSyncInfo(event_id="event_123")

        assert not_synced.is_synced is False
        assert synced.is_synced is True

    def test_google_sync_info_immutability(self):
        """
        測試 GoogleSyncInfo 是不可變的。
        """
        sync_info = GoogleSyncInfo()

        with pytest.raises(Exception):
            sync_info.event_id = "new_id"


class TestScheduleCreator:
    """測試 ScheduleCreator 值物件"""

    def test_schedule_creator_creation(self):
        """
        測試建立 ScheduleCreator。
        """
        creator = ScheduleCreator(
            user_id=TEST_CREATOR_ID,
            username="testuser",
            email="test@example.com"
        )

        assert creator.user_id == TEST_CREATOR_ID
        assert creator.username == "testuser"
        assert creator.email == "test@example.com"

    def test_schedule_creator_immutability(self):
        """
        測試 ScheduleCreator 是不可變的。
        """
        creator = ScheduleCreator(
            user_id=TEST_CREATOR_ID,
            username="testuser",
            email="test@example.com"
        )

        with pytest.raises(Exception):
            creator.username = "newuser"


class TestScheduleModelCreation:
    """測試 ScheduleModel 建立功能"""

    def test_schedule_creation_with_valid_data(self):
        """
        測試使用有效資料建立排程。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID,
            description=TEST_DESCRIPTION,
            location=TEST_LOCATION,
            timezone=TEST_TIMEZONE
        )

        assert isinstance(schedule, ScheduleModel)
        assert schedule.title == TEST_TITLE
        assert schedule.description == TEST_DESCRIPTION
        assert schedule.location == TEST_LOCATION
        assert schedule.start_time == start
        assert schedule.end_time == end
        assert schedule.creator_id == TEST_CREATOR_ID
        assert schedule.timezone == TEST_TIMEZONE
        assert schedule.all_day is False

    def test_schedule_creation_generates_uuid(self):
        """
        測試建立排程會生成有效的 UUID。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        try:
            UUID(schedule.id, version=4)
        except ValueError:
            pytest.fail("ScheduleModel.id should be a valid UUIDv4 string")

    def test_schedule_creation_generates_unique_ids(self):
        """
        測試每次建立都會生成唯一的 ID。
        """
        start, end = get_valid_time_range()
        schedule1 = ScheduleModel.create(
            title="Schedule 1",
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )
        schedule2 = ScheduleModel.create(
            title="Schedule 2",
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        assert schedule1.id != schedule2.id

    def test_schedule_creation_with_empty_title_raises_error(self):
        """
        測試使用空白標題建立排程會拋出 ValueError。
        """
        start, end = get_valid_time_range()

        with pytest.raises(ValueError, match="Title cannot be empty"):
            ScheduleModel.create(
                title="",
                start_time=start,
                end_time=end,
                creator_id=TEST_CREATOR_ID
            )

        with pytest.raises(ValueError, match="Title cannot be empty"):
            ScheduleModel.create(
                title="   ",
                start_time=start,
                end_time=end,
                creator_id=TEST_CREATOR_ID
            )

    def test_schedule_creation_strips_whitespace(self):
        """
        測試建立排程時會自動去除前後空白。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title="  Team Meeting  ",
            description="  Weekly sync  ",
            location="  Room A  ",
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        assert schedule.title == "Team Meeting"
        assert schedule.description == "Weekly sync"
        assert schedule.location == "Room A"

    def test_schedule_creation_with_invalid_time_range_raises_error(self):
        """
        測試使用無效時間範圍建立排程會拋出 ValueError。
        """
        start = datetime(2024, 1, 15, 10, 0, 0)
        end = datetime(2024, 1, 15, 9, 0, 0)  # 結束時間早於開始時間

        with pytest.raises(ValueError, match="Start time must be before end time"):
            ScheduleModel.create(
                title=TEST_TITLE,
                start_time=start,
                end_time=end,
                creator_id=TEST_CREATOR_ID
            )

    def test_schedule_creation_sets_created_at(self):
        """
        測試建立排程會設定 created_at。
        """
        start, end = get_valid_time_range()
        before = datetime.utcnow()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )
        after = datetime.utcnow()

        assert schedule.created_at is not None
        assert before <= schedule.created_at <= after
        assert schedule.updated_at is None

    def test_schedule_creation_with_all_day(self):
        """
        測試建立全天排程。
        """
        start = datetime(2024, 1, 15, 0, 0, 0)
        end = datetime(2024, 1, 16, 0, 0, 0)
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID,
            all_day=True
        )

        assert schedule.all_day is True

    def test_schedule_creation_with_optional_fields_none(self):
        """
        測試建立排程時可選欄位為 None。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        assert schedule.description is None
        assert schedule.location is None

    def test_schedule_google_sync_initially_not_synced(self):
        """
        測試新建立的排程尚未同步到 Google。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        assert schedule.google_event_id is None
        assert schedule.synced_at is None
        assert schedule.google_sync.is_synced is False


class TestScheduleModelReconstitute:
    """測試 ScheduleModel reconstitute 工廠方法"""

    def test_reconstitute_creates_schedule_from_persistence(self):
        """
        測試從持久化資料重建排程。
        """
        start, end = get_valid_time_range()
        created_at = datetime(2024, 1, 10, 8, 0, 0)
        updated_at = datetime(2024, 1, 12, 10, 0, 0)
        synced_at = datetime(2024, 1, 12, 10, 5, 0)

        schedule = ScheduleModel.reconstitute(
            id="test-uuid-123",
            title=TEST_TITLE,
            description=TEST_DESCRIPTION,
            location=TEST_LOCATION,
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            google_event_id="google_123",
            synced_at=synced_at,
            created_at=created_at,
            updated_at=updated_at
        )

        assert schedule.id == "test-uuid-123"
        assert schedule.title == TEST_TITLE
        assert schedule.description == TEST_DESCRIPTION
        assert schedule.location == TEST_LOCATION
        assert schedule.start_time == start
        assert schedule.end_time == end
        assert schedule.all_day is False
        assert schedule.timezone == TEST_TIMEZONE
        assert schedule.creator_id == TEST_CREATOR_ID
        assert schedule.google_event_id == "google_123"
        assert schedule.synced_at == synced_at
        assert schedule.created_at == created_at
        assert schedule.updated_at == updated_at

    def test_reconstitute_with_creator_info(self):
        """
        測試重建排程時包含建立者資訊。
        """
        start, end = get_valid_time_range()
        creator = ScheduleCreator(
            user_id=TEST_CREATOR_ID,
            username="testuser",
            email="test@example.com"
        )

        schedule = ScheduleModel.reconstitute(
            id="test-uuid",
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            description=None,
            location=None,
            google_event_id=None,
            synced_at=None,
            created_at=datetime.utcnow(),
            updated_at=None,
            creator=creator
        )

        assert schedule.creator is not None
        assert schedule.creator.user_id == TEST_CREATOR_ID
        assert schedule.creator.username == "testuser"
        assert schedule.creator.email == "test@example.com"


class TestScheduleModelCanEdit:
    """測試排程編輯權限"""

    def test_can_edit_returns_true_for_creator(self):
        """
        測試建立者可以編輯排程。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        assert schedule.can_edit(TEST_CREATOR_ID) is True

    def test_can_edit_returns_false_for_other_user(self):
        """
        測試非建立者無法編輯排程。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        other_user_id = "other-user-uuid"
        assert schedule.can_edit(other_user_id) is False


class TestScheduleModelUpdate:
    """測試排程更新功能"""

    def test_update_title(self):
        """
        測試更新排程標題。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        schedule.update(title="New Title")

        assert schedule.title == "New Title"
        assert schedule.updated_at is not None

    def test_update_with_empty_title_raises_error(self):
        """
        測試使用空白標題更新會拋出 ValueError。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        with pytest.raises(ValueError, match="Title cannot be empty"):
            schedule.update(title="")

        with pytest.raises(ValueError, match="Title cannot be empty"):
            schedule.update(title="   ")

    def test_update_description(self):
        """
        測試更新排程描述。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID,
            description="Old description"
        )

        schedule.update(description="New description")

        assert schedule.description == "New description"

    def test_update_location(self):
        """
        測試更新排程地點。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID,
            location="Old location"
        )

        schedule.update(location="New location")

        assert schedule.location == "New location"

    def test_update_time_range(self):
        """
        測試更新排程時間範圍。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        new_start = datetime(2024, 1, 20, 14, 0, 0)
        new_end = datetime(2024, 1, 20, 15, 0, 0)
        schedule.update(start_time=new_start, end_time=new_end)

        assert schedule.start_time == new_start
        assert schedule.end_time == new_end

    def test_update_with_invalid_time_range_raises_error(self):
        """
        測試使用無效時間範圍更新會拋出 ValueError。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        invalid_start = datetime(2024, 1, 20, 16, 0, 0)
        invalid_end = datetime(2024, 1, 20, 14, 0, 0)  # 結束時間早於開始時間

        with pytest.raises(ValueError, match="Start time must be before end time"):
            schedule.update(start_time=invalid_start, end_time=invalid_end)

    def test_update_all_day(self):
        """
        測試更新全天事件標記。
        """
        start = datetime(2024, 1, 15, 0, 0, 0)
        end = datetime(2024, 1, 16, 0, 0, 0)
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID,
            all_day=False
        )

        schedule.update(all_day=True)

        assert schedule.all_day is True

    def test_update_timezone(self):
        """
        測試更新時區。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID,
            timezone="Asia/Taipei"
        )

        schedule.update(timezone="UTC")

        assert schedule.timezone == "UTC"

    def test_update_multiple_fields(self):
        """
        測試同時更新多個欄位。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        schedule.update(
            title="Updated Title",
            description="Updated Description",
            location="Updated Location"
        )

        assert schedule.title == "Updated Title"
        assert schedule.description == "Updated Description"
        assert schedule.location == "Updated Location"

    def test_update_sets_updated_at(self):
        """
        測試更新會設定 updated_at。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        assert schedule.updated_at is None

        before = datetime.utcnow()
        schedule.update(title="New Title")
        after = datetime.utcnow()

        assert schedule.updated_at is not None
        assert before <= schedule.updated_at <= after


class TestScheduleModelGoogleSync:
    """測試排程 Google Calendar 同步功能"""

    def test_mark_synced_sets_google_event_id(self):
        """
        測試標記為已同步會設定 Google event ID。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        schedule.mark_synced("google_event_456")

        assert schedule.google_event_id == "google_event_456"
        assert schedule.synced_at is not None
        assert schedule.google_sync.is_synced is True

    def test_mark_synced_updates_synced_at(self):
        """
        測試標記為已同步會更新 synced_at。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        before = datetime.utcnow()
        schedule.mark_synced("google_event_789")
        after = datetime.utcnow()

        assert before <= schedule.synced_at <= after

    def test_mark_synced_sets_updated_at(self):
        """
        測試標記為已同步會設定 updated_at。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        schedule.mark_synced("google_event_123")

        assert schedule.updated_at is not None

    def test_clear_sync_removes_google_info(self):
        """
        測試清除同步資訊。
        """
        start, end = get_valid_time_range()
        schedule = ScheduleModel.create(
            title=TEST_TITLE,
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )
        schedule.mark_synced("google_event_123")

        schedule.clear_sync()

        assert schedule.google_event_id is None
        assert schedule.synced_at is None
        assert schedule.google_sync.is_synced is False


class TestScheduleModelEquality:
    """測試排程相等性"""

    def test_schedule_equality_by_id(self):
        """
        測試排程相等性基於 ID 判斷。
        """
        start, end = get_valid_time_range()
        schedule1 = ScheduleModel.reconstitute(
            id="same-id",
            title="Title 1",
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            description=None,
            location=None,
            google_event_id=None,
            synced_at=None,
            created_at=datetime.utcnow(),
            updated_at=None
        )
        schedule2 = ScheduleModel.reconstitute(
            id="same-id",
            title="Title 2",  # 不同標題
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            description=None,
            location=None,
            google_event_id=None,
            synced_at=None,
            created_at=datetime.utcnow(),
            updated_at=None
        )
        schedule3 = ScheduleModel.reconstitute(
            id="different-id",
            title="Title 1",
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            description=None,
            location=None,
            google_event_id=None,
            synced_at=None,
            created_at=datetime.utcnow(),
            updated_at=None
        )

        assert schedule1 == schedule2  # 相同 ID 應該相等
        assert schedule1 != schedule3  # 不同 ID 應該不相等

    def test_schedule_hash_consistency(self):
        """
        測試排程雜湊值一致性。
        """
        start, end = get_valid_time_range()
        schedule1 = ScheduleModel.reconstitute(
            id="same-id",
            title="Title 1",
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            description=None,
            location=None,
            google_event_id=None,
            synced_at=None,
            created_at=datetime.utcnow(),
            updated_at=None
        )
        schedule2 = ScheduleModel.reconstitute(
            id="same-id",
            title="Title 2",
            start_time=start,
            end_time=end,
            all_day=False,
            timezone=TEST_TIMEZONE,
            creator_id=TEST_CREATOR_ID,
            description=None,
            location=None,
            google_event_id=None,
            synced_at=None,
            created_at=datetime.utcnow(),
            updated_at=None
        )

        assert hash(schedule1) == hash(schedule2)

    def test_schedule_can_be_used_in_set(self):
        """
        測試排程可以用於集合操作。
        """
        start, end = get_valid_time_range()
        schedule1 = ScheduleModel.create(
            title="Schedule 1",
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )
        schedule2 = ScheduleModel.create(
            title="Schedule 2",
            start_time=start,
            end_time=end,
            creator_id=TEST_CREATOR_ID
        )

        schedule_set = {schedule1, schedule2}

        assert len(schedule_set) == 2
