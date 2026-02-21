"""
Unit tests for UserRepository and UserQueryRepository.
Tests the data access layer for User aggregate persistence.

測試策略:
- 使用 SQLite in-memory 資料庫進行真實 ORM 操作
- 驗證 ORM → Domain Model 的轉換正確性
- 覆蓋所有 CRUD 操作和查詢功能
"""
import pytest
from datetime import date
from uuid import uuid4
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.UserRepository import UserRepository, UserQueryRepository
from app.domain.UserModel import UserModel, UserRole, AccountType
from database.models.user import User, Profile


class TestUserRepositoryAdd:
    """測試 UserRepository.add 新增使用者功能"""

    def test_add_user_with_profile(self, test_db_session: Session):
        """測試新增使用者及其個人資料"""
        repo = UserRepository(test_db_session)
        user_id = uuid4()

        user = repo.add(
            user_dict={
                "id": user_id,
                "uid": "newuser",
                "pwd": "hashed_password",
                "email": "new@example.com",
                "role": UserRole.NORMAL,
            },
            profile_dict={"name": "New User", "birthdate": date(1990, 1, 1)},
        )
        test_db_session.commit()

        assert user.id == user_id
        assert user.uid == "newuser"
        assert user.email == "new@example.com"
        assert user.profile is not None
        assert user.profile.name == "New User"


class TestUserRepositoryGetBy:
    """測試 UserRepository 的各種查詢方法"""

    def test_get_by_uid_existing(self, test_db_session: Session, sample_users):
        """測試以 uid 查詢存在的使用者"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_uid("user1")

        assert result is not None
        assert isinstance(result, UserModel)
        assert result.uid == "user1"

    def test_get_by_uid_non_existing(self, test_db_session: Session):
        """測試以 uid 查詢不存在的使用者"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_uid("nonexistent")
        assert result is None

    def test_get_by_id_existing(self, test_db_session: Session, sample_users):
        """測試以 UUID 查詢存在的使用者"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)
        result = repo.get_by_id(user_id)

        assert result is not None
        assert result.id == user_id

    def test_get_by_id_non_existing(self, test_db_session: Session):
        """測試以 UUID 查詢不存在的使用者"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_id(str(uuid4()))
        assert result is None

    def test_get_by_email_existing(self, test_db_session: Session, sample_users):
        """測試以 email 查詢存在的使用者"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_email("user1@example.com")

        assert result is not None
        assert result.email == "user1@example.com"

    def test_get_by_email_non_existing(self, test_db_session: Session):
        """測試以 email 查詢不存在的使用者"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_email("nonexistent@example.com")
        assert result is None


class TestUserRepositoryExists:
    """測試 UserRepository 的存在檢查方法"""

    def test_exists_by_uid_true(self, test_db_session: Session, sample_users):
        """測試 uid 存在時回傳 True"""
        repo = UserRepository(test_db_session)
        assert repo.exists_by_uid("user1") is True

    def test_exists_by_uid_false(self, test_db_session: Session):
        """測試 uid 不存在時回傳 False"""
        repo = UserRepository(test_db_session)
        assert repo.exists_by_uid("nonexistent") is False

    def test_exists_by_email_true(self, test_db_session: Session, sample_users):
        """測試 email 存在時回傳 True"""
        repo = UserRepository(test_db_session)
        assert repo.exists_by_email("user1@example.com") is True

    def test_exists_by_email_false(self, test_db_session: Session):
        """測試 email 不存在時回傳 False"""
        repo = UserRepository(test_db_session)
        assert repo.exists_by_email("nonexistent@example.com") is False


class TestUserRepositoryUpdate:
    """測試 UserRepository 的更新方法"""

    def test_update_profile(self, test_db_session: Session):
        """測試更新使用者個人資料"""
        repo = UserRepository(test_db_session)
        user_id = uuid4()

        # 透過 repo.add 建立使用者（包含 profile）
        repo.add(
            user_dict={"id": user_id, "uid": "profuser", "pwd": "hash", "email": "prof@example.com"},
            profile_dict={"name": "Old Name", "birthdate": date(1990, 1, 1)},
        )
        test_db_session.commit()

        result = repo.update_profile(
            user_id=str(user_id),
            name="Updated Name",
            birthdate=date(1995, 5, 15),
            description="Updated description",
        )
        test_db_session.commit()

        assert result is not None
        assert result.profile.name == "Updated Name"
        assert result.profile.birthdate == date(1995, 5, 15)
        assert result.profile.description == "Updated description"

    def test_update_profile_user_not_found(self, test_db_session: Session):
        """測試更新不存在使用者的個人資料"""
        repo = UserRepository(test_db_session)
        result = repo.update_profile(str(uuid4()), "name", date(1990, 1, 1), "desc")
        assert result is None

    def test_update_password(self, test_db_session: Session, sample_users):
        """測試更新密碼"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        result = repo.update_password(user_id, "new_hashed_password")
        test_db_session.commit()

        assert result is True
        updated = repo.get_by_id(user_id)
        assert updated._hashed_password.value == "new_hashed_password"

    def test_update_password_user_not_found(self, test_db_session: Session):
        """測試更新不存在使用者的密碼"""
        repo = UserRepository(test_db_session)
        result = repo.update_password(str(uuid4()), "new_hash")
        assert result is False

    def test_update_role(self, test_db_session: Session, sample_users):
        """測試更新使用者角色"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        result = repo.update_role(user_id, UserRole.ADMIN)
        test_db_session.commit()

        assert result is True
        updated = repo.get_by_id(user_id)
        assert updated.role == UserRole.ADMIN

    def test_update_role_user_not_found(self, test_db_session: Session):
        """測試更新不存在使用者的角色"""
        repo = UserRepository(test_db_session)
        result = repo.update_role(str(uuid4()), UserRole.ADMIN)
        assert result is False

    def test_verify_email(self, test_db_session: Session, sample_users):
        """測試驗證使用者 Email"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        result = repo.verify_email(user_id)
        test_db_session.commit()

        assert result is True
        updated = repo.get_by_id(user_id)
        assert updated.email_verified is True

    def test_verify_email_user_not_found(self, test_db_session: Session):
        """測試驗證不存在使用者的 Email"""
        repo = UserRepository(test_db_session)
        result = repo.verify_email(str(uuid4()))
        assert result is False

    def test_update_avatar(self, test_db_session: Session):
        """測試更新使用者頭像"""
        repo = UserRepository(test_db_session)
        user_id = uuid4()

        repo.add(
            user_dict={"id": user_id, "uid": "avataruser", "pwd": "hash", "email": "avatar@example.com"},
            profile_dict={"name": "User", "birthdate": date(1990, 1, 1)},
        )
        test_db_session.commit()

        result = repo.update_avatar(str(user_id), "https://example.com/avatar.png")
        test_db_session.commit()

        assert result == "https://example.com/avatar.png"

    def test_update_avatar_user_not_found(self, test_db_session: Session):
        """測試更新不存在使用者的頭像"""
        repo = UserRepository(test_db_session)
        result = repo.update_avatar(str(uuid4()), "https://example.com/avatar.png")
        assert result is None


class TestUserRepositoryOAuth:
    """測試 UserRepository 的 OAuth 相關方法"""

    def test_link_google_id(self, test_db_session: Session, sample_users):
        """測試連結 Google 帳號"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        result = repo.link_google_id(user_id, "google_123")
        test_db_session.commit()

        assert result is True

    def test_get_by_google_id(self, test_db_session: Session, sample_users):
        """測試以 Google ID 查詢使用者"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        repo.link_google_id(user_id, "google_456")
        test_db_session.commit()

        result = repo.get_by_google_id("google_456")
        assert result is not None
        assert result.id == user_id

    def test_get_by_google_id_not_found(self, test_db_session: Session):
        """測試以不存在的 Google ID 查詢"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_google_id("nonexistent")
        assert result is None

    def test_link_github_id(self, test_db_session: Session, sample_users):
        """測試連結 GitHub 帳號"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        result = repo.link_github_id(user_id, "github_123")
        test_db_session.commit()

        assert result is True

    def test_get_by_github_id(self, test_db_session: Session, sample_users):
        """測試以 GitHub ID 查詢使用者"""
        repo = UserRepository(test_db_session)
        user_id = str(sample_users[0].id)

        repo.link_github_id(user_id, "github_456")
        test_db_session.commit()

        result = repo.get_by_github_id("github_456")
        assert result is not None
        assert result.id == user_id

    def test_get_by_github_id_not_found(self, test_db_session: Session):
        """測試以不存在的 GitHub ID 查詢"""
        repo = UserRepository(test_db_session)
        result = repo.get_by_github_id("nonexistent")
        assert result is None

    def test_link_google_id_user_not_found(self, test_db_session: Session):
        """測試連結不存在使用者的 Google 帳號"""
        repo = UserRepository(test_db_session)
        result = repo.link_google_id(str(uuid4()), "google_123")
        assert result is False

    def test_link_github_id_user_not_found(self, test_db_session: Session):
        """測試連結不存在使用者的 GitHub 帳號"""
        repo = UserRepository(test_db_session)
        result = repo.link_github_id(str(uuid4()), "github_123")
        assert result is False


class TestUserQueryRepository:
    """測試 UserQueryRepository 的查詢方法"""

    def test_get_all_returns_users(self, test_db_session: Session, sample_users):
        """測試取得所有使用者（分頁）"""
        repo = UserQueryRepository(test_db_session)
        users, total = repo.get_all(page=1, size=10)

        assert total == 3
        assert len(users) == 3
        assert all(isinstance(u, UserModel) for u in users)

    def test_get_all_pagination(self, test_db_session: Session, sample_users):
        """測試分頁功能"""
        repo = UserQueryRepository(test_db_session)

        users, total = repo.get_all(page=1, size=2)
        assert total == 3
        assert len(users) == 2

        users2, total2 = repo.get_all(page=2, size=2)
        assert total2 == 3
        assert len(users2) == 1

    def test_get_all_empty(self, test_db_session: Session):
        """測試沒有使用者時的結果"""
        repo = UserQueryRepository(test_db_session)
        users, total = repo.get_all(page=1, size=10)
        assert total == 0
        assert len(users) == 0

    def test_search_users_by_uid(self, test_db_session: Session, sample_users):
        """測試以 uid 搜尋使用者"""
        repo = UserQueryRepository(test_db_session)
        users, total = repo.search_users("user1")

        assert total >= 1
        assert any(u.uid == "user1" for u in users)

    def test_search_users_by_email(self, test_db_session: Session, sample_users):
        """測試以 email 搜尋使用者"""
        repo = UserQueryRepository(test_db_session)
        users, total = repo.search_users("admin@example.com")

        assert total >= 1
        assert any(u.email == "admin@example.com" for u in users)

    def test_search_users_exclude_user(self, test_db_session: Session, sample_users):
        """測試搜尋時排除指定使用者"""
        repo = UserQueryRepository(test_db_session)
        exclude_id = str(sample_users[0].id)
        users, total = repo.search_users("user", exclude_user_id=exclude_id)

        assert all(u.id != exclude_id for u in users)

    def test_search_users_no_results(self, test_db_session: Session, sample_users):
        """測試搜尋沒有結果"""
        repo = UserQueryRepository(test_db_session)
        users, total = repo.search_users("zzz_nonexistent_zzz")
        assert total == 0
        assert len(users) == 0
