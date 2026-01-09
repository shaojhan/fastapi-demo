import pytest
from datetime import date
from uuid import UUID
from app.domain.UserModel import (
    UserModel,
    UserRole,
    Profile,
    HashedPassword,
)

# --- Test Data ---
TEST_UID = "testuser123"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "plain_password_123"

def test_user_registration_creates_valid_user():
    """
    測試 `register` 工廠方法是否能正確建立一個新的使用者。
    """
    user = UserModel.register(
        uid=TEST_UID,
        raw_password=TEST_PASSWORD,
        email=TEST_EMAIL
    )

    # 斷言物件型別正確
    assert isinstance(user, UserModel)
    
    # 斷言 ID 是一個有效的 UUID
    try:
        UUID(user.id, version=4)
    except ValueError:
        pytest.fail("UserModel.id should be a valid UUIDv4 string")

    # 斷言初始屬性符合預期
    assert user.uid == TEST_UID
    assert user.email == TEST_EMAIL
    assert user.role == UserRole.NORMAL
    assert user.profile == Profile() # 初始 Profile 應為空

def test_password_verification():
    """
    測試 `verify_password` 方法的正確性。
    """
    user = UserModel.register(
        uid=TEST_UID,
        raw_password=TEST_PASSWORD,
        email=TEST_EMAIL
    )

    # 斷言正確的密碼可以通過驗證
    assert user.verify_password(TEST_PASSWORD) is True

    # 斷言錯誤的密碼無法通過驗證
    assert user.verify_password("wrong_password") is False

def test_profile_update():
    """
    測試 `update_profile` 方法是否能成功更新使用者的個人資料。
    """
    user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL)

    new_name = "John Doe"
    new_birthdate = date(1990, 1, 15)
    new_description = "A software developer."

    user.update_profile(name=new_name, birthdate=new_birthdate, description=new_description)

    assert user.profile.name == new_name
    assert user.profile.birthdate == new_birthdate
    assert user.profile.description == new_description