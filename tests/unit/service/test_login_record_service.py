"""
Unit tests for LoginRecordService and LoginRecordQueryService.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from uuid import uuid4

from app.services.LoginRecordService import LoginRecordService, LoginRecordQueryService
from app.domain.LoginRecordModel import LoginRecordModel


# --- Test Data ---
TEST_USER_ID = str(uuid4())
TEST_USERNAME = "testuser"
TEST_IP = "192.168.1.100"
TEST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0)"


def _make_login_record(
    success=True,
    user_id=None,
    failure_reason=None,
) -> LoginRecordModel:
    """Create a test LoginRecordModel."""
    return LoginRecordModel.reconstitute(
        id=str(uuid4()),
        username=TEST_USERNAME,
        ip_address=TEST_IP,
        user_agent=TEST_USER_AGENT,
        success=success,
        created_at=datetime.now(),
        user_id=user_id or TEST_USER_ID,
        failure_reason=failure_reason,
    )


class TestLoginRecordService:
    """Tests for LoginRecordService.record_login"""

    @patch("app.services.LoginRecordService.LoginRecordUnitOfWork")
    def test_record_successful_login(self, mock_uow_class):
        """測試記錄成功的登錄"""
        mock_repo = MagicMock()
        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordService()
        service.record_login(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=True,
            user_id=TEST_USER_ID,
        )

        mock_repo.add.assert_called_once()
        call_args = mock_repo.add.call_args[0][0]
        assert call_args["username"] == TEST_USERNAME
        assert call_args["ip_address"] == TEST_IP
        assert call_args["user_agent"] == TEST_USER_AGENT
        assert call_args["success"] is True
        assert call_args["failure_reason"] is None

    @patch("app.services.LoginRecordService.LoginRecordUnitOfWork")
    def test_record_failed_login(self, mock_uow_class):
        """測試記錄失敗的登錄"""
        mock_repo = MagicMock()
        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordService()
        service.record_login(
            username=TEST_USERNAME,
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=False,
            failure_reason="密碼錯誤",
            user_id=TEST_USER_ID,
        )

        mock_repo.add.assert_called_once()
        call_args = mock_repo.add.call_args[0][0]
        assert call_args["success"] is False
        assert call_args["failure_reason"] == "密碼錯誤"

    @patch("app.services.LoginRecordService.LoginRecordUnitOfWork")
    def test_record_login_without_user_id(self, mock_uow_class):
        """測試記錄帳號不存在的失敗登錄（無 user_id）"""
        mock_repo = MagicMock()
        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordService()
        service.record_login(
            username="nonexistent",
            ip_address=TEST_IP,
            user_agent=TEST_USER_AGENT,
            success=False,
            failure_reason="帳號不存在",
        )

        mock_repo.add.assert_called_once()
        call_args = mock_repo.add.call_args[0][0]
        assert call_args["user_id"] is None
        assert call_args["failure_reason"] == "帳號不存在"


class TestLoginRecordQueryService:
    """Tests for LoginRecordQueryService"""

    @patch("app.services.LoginRecordService.LoginRecordQueryUnitOfWork")
    def test_get_my_records(self, mock_uow_class):
        """測試查詢自己的登錄紀錄"""
        records = [_make_login_record(), _make_login_record()]

        mock_query_repo = MagicMock()
        mock_query_repo.get_by_user_id.return_value = (records, 2)

        mock_uow = MagicMock()
        mock_uow.query_repo = mock_query_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordQueryService()
        result_records, total = service.get_my_records(TEST_USER_ID, page=1, size=20)

        assert len(result_records) == 2
        assert total == 2
        mock_query_repo.get_by_user_id.assert_called_once_with(TEST_USER_ID, 1, 20)

    @patch("app.services.LoginRecordService.LoginRecordQueryUnitOfWork")
    def test_get_all_records(self, mock_uow_class):
        """測試管理員查詢所有登錄紀錄"""
        records = [_make_login_record(), _make_login_record(), _make_login_record()]

        mock_query_repo = MagicMock()
        mock_query_repo.get_all.return_value = (records, 3)

        mock_uow = MagicMock()
        mock_uow.query_repo = mock_query_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordQueryService()
        result_records, total = service.get_all_records(page=1, size=20)

        assert len(result_records) == 3
        assert total == 3
        mock_query_repo.get_all.assert_called_once_with(1, 20, None)

    @patch("app.services.LoginRecordService.LoginRecordQueryUnitOfWork")
    def test_get_all_records_with_user_id_filter(self, mock_uow_class):
        """測試管理員依 user_id 篩選登錄紀錄"""
        records = [_make_login_record()]

        mock_query_repo = MagicMock()
        mock_query_repo.get_all.return_value = (records, 1)

        mock_uow = MagicMock()
        mock_uow.query_repo = mock_query_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordQueryService()
        result_records, total = service.get_all_records(page=1, size=20, user_id=TEST_USER_ID)

        assert len(result_records) == 1
        assert total == 1
        mock_query_repo.get_all.assert_called_once_with(1, 20, TEST_USER_ID)

    @patch("app.services.LoginRecordService.LoginRecordQueryUnitOfWork")
    def test_get_my_records_empty(self, mock_uow_class):
        """測試查詢無紀錄的結果"""
        mock_query_repo = MagicMock()
        mock_query_repo.get_by_user_id.return_value = ([], 0)

        mock_uow = MagicMock()
        mock_uow.query_repo = mock_query_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = LoginRecordQueryService()
        result_records, total = service.get_my_records(str(uuid4()), page=1, size=20)

        assert len(result_records) == 0
        assert total == 0
