"""
Unit tests for UserService.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from uuid import uuid4

from app.services.UserService import UserService
from app.domain.UserModel import UserModel, UserRole, Profile
from app.exceptions.UserException import (
    UserNotFoundError, AuthenticationError, UserHasAlreadyExistedError,
    EmailAlreadyRegisteredError, EmailNotVerifiedYetError
)


# --- Test Data ---
TEST_USER_ID = str(uuid4())
TEST_UID = "testuser"
TEST_EMAIL = "test@example.com"


def _make_user_model(
    user_id=None,
    name="Original Name",
    birthdate=date(1990, 1, 1),
    description="Original description"
) -> UserModel:
    """建立測試用的 UserModel。"""
    return UserModel.reconstitute(
        id=user_id or TEST_USER_ID,
        uid=TEST_UID,
        email=TEST_EMAIL,
        hashed_password="hashed_password",
        profile=Profile(name=name, birthdate=birthdate, description=description),
        role=UserRole.NORMAL
    )


class TestUpdateUserProfile:
    """測試 UserService.update_user_profile"""

    @patch("app.services.UserService.UserUnitOfWork")
    def test_update_profile_success(self, mock_uow_class):
        """
        測試成功更新使用者個人資料。
        """
        # Arrange
        new_name = "New Name"
        new_birthdate = date(1995, 6, 15)
        new_description = "Updated description"

        updated_user = _make_user_model(
            name=new_name,
            birthdate=new_birthdate,
            description=new_description
        )

        mock_repo = MagicMock()
        mock_repo.update_profile.return_value = updated_user

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = UserService()
        result = service.update_user_profile(
            user_id=TEST_USER_ID,
            name=new_name,
            birthdate=new_birthdate,
            description=new_description
        )

        # Assert
        mock_repo.update_profile.assert_called_once_with(
            user_id=TEST_USER_ID,
            name=new_name,
            birthdate=new_birthdate,
            description=new_description
        )
        mock_uow.commit.assert_called_once()

        assert result.profile.name == new_name
        assert result.profile.birthdate == new_birthdate
        assert result.profile.description == new_description

    @patch("app.services.UserService.UserUnitOfWork")
    def test_update_profile_user_not_found(self, mock_uow_class):
        """
        測試更新不存在的使用者時拋出 UserNotFoundError。
        """
        # Arrange
        mock_repo = MagicMock()
        mock_repo.update_profile.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = UserService()
        with pytest.raises(UserNotFoundError):
            service.update_user_profile(
                user_id=str(uuid4()),
                name="Name",
                birthdate=date(1990, 1, 1),
                description="Desc"
            )

        mock_uow.commit.assert_not_called()

    @patch("app.services.UserService.UserUnitOfWork")
    def test_update_profile_passes_correct_args_to_repo(self, mock_uow_class):
        """
        測試 Service 正確傳遞參數給 Repository。
        """
        # Arrange
        user_id = str(uuid4())
        name = "張三"
        birthdate = date(2000, 12, 25)
        description = "測試自我介紹"

        mock_repo = MagicMock()
        mock_repo.update_profile.return_value = _make_user_model(
            user_id=user_id, name=name, birthdate=birthdate, description=description
        )

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = UserService()
        service.update_user_profile(
            user_id=user_id,
            name=name,
            birthdate=birthdate,
            description=description
        )

        # Assert
        mock_repo.update_profile.assert_called_once_with(
            user_id=user_id,
            name=name,
            birthdate=birthdate,
            description=description
        )


class TestUpdatePassword:
    """測試 UserService.update_password"""

    @patch("app.services.UserService.UserUnitOfWork")
    @patch("app.services.UserService.pwd_context")
    def test_update_password_success(self, mock_pwd_context, mock_uow_class):
        """
        測試成功更新密碼。
        """
        # Arrange
        mock_pwd_context.verify.return_value = True
        mock_pwd_context.hash.return_value = "hashed_new_password"

        user = _make_user_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = user
        mock_repo.update_password.return_value = True

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = UserService()
        service.update_password(
            user_id=TEST_USER_ID,
            old_password="old_pass",
            new_password="new_pass"
        )

        # Assert
        mock_repo.get_by_id.assert_called_once_with(TEST_USER_ID)
        mock_repo.update_password.assert_called_once_with(
            user_id=TEST_USER_ID,
            new_hashed_password="hashed_new_password"
        )
        mock_uow.commit.assert_called_once()

    @patch("app.services.UserService.UserUnitOfWork")
    def test_update_password_user_not_found(self, mock_uow_class):
        """
        測試更新不存在使用者的密碼時拋出 UserNotFoundError。
        """
        # Arrange
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = UserService()
        with pytest.raises(UserNotFoundError):
            service.update_password(
                user_id=str(uuid4()),
                old_password="old_pass",
                new_password="new_pass"
            )

        mock_uow.commit.assert_not_called()

    @patch("app.services.UserService.UserUnitOfWork")
    @patch("app.services.UserService.pwd_context")
    def test_update_password_wrong_old_password(self, mock_pwd_context, mock_uow_class):
        """
        測試舊密碼錯誤時拋出 AuthenticationError。
        """
        # Arrange
        mock_pwd_context.verify.return_value = False

        user = _make_user_model()

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = user

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = UserService()
        with pytest.raises(AuthenticationError):
            service.update_password(
                user_id=TEST_USER_ID,
                old_password="wrong_password",
                new_password="new_pass"
            )

        mock_repo.update_password.assert_not_called()
        mock_uow.commit.assert_not_called()


class TestAddUserProfile:
    """Tests for UserService.add_user_profile email uniqueness check."""

    def _make_user_schema(self):
        from app.router.schemas.UserSchema import UserSchema
        return UserSchema(
            uid="newuser",
            pwd="P@ssword123",
            email="new@example.com",
            name="New User",
            birthdate=date(1990, 1, 1),
            description="",
        )

    @patch("app.services.UserService.generate_verification_token", return_value="mock-token")
    @patch("app.services.UserService.UserUnitOfWork")
    def test_register_success(self, mock_uow_class, mock_gen_token):
        mock_repo = MagicMock()
        mock_repo.exists_by_uid.return_value = False
        mock_repo.get_by_email.return_value = None
        mock_repo.add.return_value = _make_user_model()

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = UserService()
        result = service.add_user_profile(self._make_user_schema())
        assert result is not None
        mock_repo.add.assert_called_once()

    @patch("app.services.UserService.UserUnitOfWork")
    def test_register_uid_exists(self, mock_uow_class):
        mock_repo = MagicMock()
        mock_repo.exists_by_uid.return_value = True

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = UserService()
        with pytest.raises(UserHasAlreadyExistedError):
            service.add_user_profile(self._make_user_schema())

    @patch("app.services.UserService.UserUnitOfWork")
    def test_register_email_exists_verified(self, mock_uow_class):
        existing_user = _make_user_model()
        existing_user._email_verified = True

        mock_repo = MagicMock()
        mock_repo.exists_by_uid.return_value = False
        mock_repo.get_by_email.return_value = existing_user

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = UserService()
        with pytest.raises(EmailAlreadyRegisteredError):
            service.add_user_profile(self._make_user_schema())

    @patch("app.services.UserService.UserUnitOfWork")
    def test_register_email_exists_not_verified(self, mock_uow_class):
        existing_user = _make_user_model()
        existing_user._email_verified = False

        mock_repo = MagicMock()
        mock_repo.exists_by_uid.return_value = False
        mock_repo.get_by_email.return_value = existing_user

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = UserService()
        with pytest.raises(EmailNotVerifiedYetError):
            service.add_user_profile(self._make_user_schema())

    @patch("app.services.UserService.generate_verification_token", return_value="mock-token")
    @patch("app.services.UserService.UserUnitOfWork")
    def test_register_always_creates_normal_role(self, mock_uow_class, mock_gen_token):
        """安全測試：無論輸入為何，新使用者的 role 一律被強制設為 NORMAL。"""
        mock_repo = MagicMock()
        mock_repo.exists_by_uid.return_value = False
        mock_repo.get_by_email.return_value = None
        mock_repo.add.return_value = _make_user_model()

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = UserService()
        service.add_user_profile(self._make_user_schema())

        # 驗證傳給 repo.add() 的 user_dict role 必須是 'NORMAL'
        call_args = mock_repo.add.call_args
        user_dict = call_args[0][0]
        assert user_dict["role"] == "NORMAL"
