"""
Unit tests for LoginRecordRepository.
Tests the data access layer for LoginRecord.
"""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.LoginRecordRepository import (
    LoginRecordRepository,
    LoginRecordQueryRepository,
)
from app.domain.LoginRecordModel import LoginRecordModel
from database.models.login_record import LoginRecord


class TestLoginRecordRepository:
    """Test suite for LoginRecordRepository write operations."""

    def test_add_login_record(self, test_db_session: Session, sample_users):
        """測試新增登錄紀錄"""
        repo = LoginRecordRepository(test_db_session)
        user = sample_users[0]

        record_dict = {
            "id": uuid4(),
            "user_id": user.id,
            "username": "user1",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
            "success": True,
            "failure_reason": None,
        }

        result = repo.add(record_dict)

        assert result.id is not None
        assert result.username == "user1"
        assert result.ip_address == "192.168.1.100"
        assert result.success is True
        assert result.created_at is not None

    def test_add_failed_login_record(self, test_db_session: Session):
        """測試新增失敗登錄紀錄（無 user_id）"""
        repo = LoginRecordRepository(test_db_session)

        record_dict = {
            "id": uuid4(),
            "user_id": None,
            "username": "unknown_user",
            "ip_address": "10.0.0.1",
            "user_agent": "curl/7.88",
            "success": False,
            "failure_reason": "帳號不存在",
        }

        result = repo.add(record_dict)

        assert result.user_id is None
        assert result.success is False
        assert result.failure_reason == "帳號不存在"


class TestLoginRecordQueryRepository:
    """Test suite for LoginRecordQueryRepository read operations."""

    def test_get_by_user_id(self, test_db_session: Session, sample_login_records, sample_users):
        """測試依 user_id 查詢登錄紀錄"""
        repo = LoginRecordQueryRepository(test_db_session)
        user1 = sample_users[0]

        records, total = repo.get_by_user_id(str(user1.id), page=1, size=10)

        assert total == 2  # user1 has 2 records
        assert len(records) == 2
        for r in records:
            assert r.user_id == str(user1.id)

    def test_get_by_user_id_pagination(self, test_db_session: Session, sample_login_records, sample_users):
        """測試分頁查詢"""
        repo = LoginRecordQueryRepository(test_db_session)
        user1 = sample_users[0]

        records, total = repo.get_by_user_id(str(user1.id), page=1, size=1)

        assert total == 2
        assert len(records) == 1

    def test_get_by_user_id_no_records(self, test_db_session: Session, sample_login_records):
        """測試查詢無紀錄的使用者"""
        repo = LoginRecordQueryRepository(test_db_session)
        fake_user_id = str(uuid4())

        records, total = repo.get_by_user_id(fake_user_id, page=1, size=10)

        assert total == 0
        assert len(records) == 0

    def test_get_all(self, test_db_session: Session, sample_login_records):
        """測試查詢所有登錄紀錄"""
        repo = LoginRecordQueryRepository(test_db_session)

        records, total = repo.get_all(page=1, size=10)

        assert total == 4  # 4 sample records
        assert len(records) == 4

    def test_get_all_with_user_id_filter(self, test_db_session: Session, sample_login_records, sample_users):
        """測試查詢所有紀錄並依 user_id 篩選"""
        repo = LoginRecordQueryRepository(test_db_session)
        user2 = sample_users[1]

        records, total = repo.get_all(page=1, size=10, user_id=str(user2.id))

        assert total == 1
        assert len(records) == 1
        assert records[0].username == "user2"

    def test_get_all_pagination(self, test_db_session: Session, sample_login_records):
        """測試分頁查詢所有紀錄"""
        repo = LoginRecordQueryRepository(test_db_session)

        records_page1, total = repo.get_all(page=1, size=2)
        records_page2, _ = repo.get_all(page=2, size=2)

        assert total == 4
        assert len(records_page1) == 2
        assert len(records_page2) == 2

    def test_to_domain_model(self, test_db_session: Session, sample_login_records):
        """測試 ORM -> Domain Model 轉換"""
        repo = LoginRecordQueryRepository(test_db_session)

        records, _ = repo.get_all(page=1, size=10)

        for r in records:
            assert isinstance(r, LoginRecordModel)
            assert r.id is not None
            assert r.username is not None
            assert r.ip_address is not None
            assert r.user_agent is not None
            assert isinstance(r.success, bool)
            assert r.created_at is not None

    def test_results_ordered_by_created_at_desc(self, test_db_session: Session, sample_users):
        """測試結果依 created_at 降序排列"""
        from datetime import datetime, timedelta

        repo = LoginRecordQueryRepository(test_db_session)
        user = sample_users[0]

        # Insert records with specific times
        for i in range(3):
            test_db_session.add(LoginRecord(
                id=uuid4(),
                user_id=user.id,
                username="user1",
                ip_address="1.1.1.1",
                user_agent="test",
                success=True,
                created_at=datetime(2026, 1, 1 + i),
            ))
        test_db_session.commit()

        records, _ = repo.get_by_user_id(str(user.id), page=1, size=10)

        # Should be newest first
        for i in range(len(records) - 1):
            assert records[i].created_at >= records[i + 1].created_at
