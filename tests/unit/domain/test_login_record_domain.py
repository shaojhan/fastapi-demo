"""
Unit tests for LoginRecordModel domain model.
"""
import pytest
from datetime import datetime
from uuid import UUID

from app.domain.LoginRecordModel import LoginRecordModel


# --- Test Data ---
TEST_USERNAME = "testuser"
TEST_IP = "192.168.1.100"
TEST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


class TestLoginRecordCreate:
    """測試 LoginRecordModel.create 工廠方法"""

    def test_create_successful_login_record(self):
        """測試建立成功的登錄紀錄"""
        record = LoginRecordModel.create(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=True,
            user_id=TEST_USER_ID,
        )

        assert isinstance(record, LoginRecordModel)
        # ID 應為有效 UUID
        try:
            UUID(record.id, version=4)
        except ValueError:
            pytest.fail("LoginRecordModel.id should be a valid UUIDv4 string")

        assert record.username == TEST_USERNAME
        assert record.ip_address == TEST_IP
        assert record.user_agent == TEST_USER_AGENT
        assert record.success is True
        assert record.user_id == TEST_USER_ID
        assert record.failure_reason is None
        assert isinstance(record.created_at, datetime)

    def test_create_failed_login_record(self):
        """測試建立失敗的登錄紀錄"""
        record = LoginRecordModel.create(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=False,
            failure_reason="密碼錯誤",
        )

        assert record.success is False
        assert record.failure_reason == "密碼錯誤"
        assert record.user_id is None

    def test_create_failed_login_with_user_id(self):
        """測試建立有 user_id 的失敗紀錄（帳號存在但密碼錯誤）"""
        record = LoginRecordModel.create(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=False,
            user_id=TEST_USER_ID,
            failure_reason="密碼錯誤",
        )

        assert record.success is False
        assert record.user_id == TEST_USER_ID
        assert record.failure_reason == "密碼錯誤"

    def test_create_failed_login_without_user_id(self):
        """測試帳號不存在時的失敗紀錄（無 user_id）"""
        record = LoginRecordModel.create(
            username="nonexistent",
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=False,
            failure_reason="帳號不存在",
        )

        assert record.user_id is None
        assert record.failure_reason == "帳號不存在"

    def test_create_generates_unique_ids(self):
        """測試每次建立都會產生唯一 ID"""
        record1 = LoginRecordModel.create(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=True,
        )
        record2 = LoginRecordModel.create(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=True,
        )

        assert record1.id != record2.id


class TestLoginRecordReconstitute:
    """測試 LoginRecordModel.reconstitute 工廠方法"""

    def test_reconstitute_from_persistence(self):
        """測試從持久化資料重建"""
        created_at = datetime(2026, 2, 18, 10, 30, 0)
        record = LoginRecordModel.reconstitute(
            id="test-uuid",
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=True,
            created_at=created_at,
            user_id=TEST_USER_ID,
        )

        assert record.id == "test-uuid"
        assert record.username == TEST_USERNAME
        assert record.ip_address == TEST_IP
        assert record.user_agent == TEST_USER_AGENT
        assert record.success is True
        assert record.created_at == created_at
        assert record.user_id == TEST_USER_ID
        assert record.failure_reason is None

    def test_reconstitute_failed_record(self):
        """測試重建失敗的登錄紀錄"""
        record = LoginRecordModel.reconstitute(
            id="test-uuid",
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=False,
            created_at=datetime(2026, 2, 18, 10, 30, 0),
            failure_reason="密碼錯誤",
        )

        assert record.success is False
        assert record.failure_reason == "密碼錯誤"
        assert record.user_id is None


class TestLoginRecordProperties:
    """測試 LoginRecordModel 屬性"""

    def test_all_properties_are_accessible(self):
        """測試所有屬性都可以存取"""
        record = LoginRecordModel.create(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=True,
            user_id=TEST_USER_ID,
            failure_reason=None,
        )

        # All properties should be accessible without error
        assert record.id is not None
        assert record.username == TEST_USERNAME
        assert record.ip_address == TEST_IP
        assert record.user_agent == TEST_USER_AGENT
        assert record.success is True
        assert record.user_id == TEST_USER_ID
        assert record.failure_reason is None
        assert record.created_at is not None
