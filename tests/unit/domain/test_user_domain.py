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


# --- Test Helper Functions ---
def mock_hash_func(password: str) -> str:
    """Mock hash function for testing."""
    return f"hashed_{password}"


def mock_verify_func(raw_password: str, hashed_password: str) -> bool:
    """Mock verify function for testing."""
    return hashed_password == f"hashed_{raw_password}"


class TestUserRegistration:
    """測試使用者註冊相關功能"""

    def test_user_registration_creates_valid_user(self):
        """
        測試 `register` 工廠方法是否能正確建立一個新的使用者。
        """
        user = UserModel.register(
            uid=TEST_UID,
            raw_password=TEST_PASSWORD,
            email=TEST_EMAIL,
            hash_func=mock_hash_func
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
        assert user.profile == Profile()  # 初始 Profile 應為空

    def test_user_registration_generates_unique_ids(self):
        """
        測試每次註冊都會生成唯一的 ID
        """
        user1 = UserModel.register("user1", "password1", "user1@example.com", mock_hash_func)
        user2 = UserModel.register("user2", "password2", "user2@example.com", mock_hash_func)

        assert user1.id != user2.id

    def test_user_registration_hashes_password(self):
        """
        測試密碼在註冊時會被雜湊處理
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)

        # 確保密碼已經被雜湊（使用 mock hash function）
        assert user._hashed_password.value == f"hashed_{TEST_PASSWORD}"
        assert user._hashed_password.value != TEST_PASSWORD

    def test_user_registration_with_empty_profile(self):
        """
        測試新註冊的使用者有空的個人資料
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)

        assert user.profile.name is None
        assert user.profile.birthdate is None
        assert user.profile.description is None


class TestPasswordVerification:
    """測試密碼驗證功能"""

    def test_password_verification_with_correct_password(self):
        """
        測試使用正確的密碼進行驗證
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)
        assert user.verify_password(TEST_PASSWORD, mock_verify_func) is True

    def test_password_verification_with_wrong_password(self):
        """
        測試使用錯誤的密碼進行驗證
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)
        assert user.verify_password("wrong_password", mock_verify_func) is False

    def test_password_verification_case_sensitive(self):
        """
        測試密碼驗證是否區分大小寫
        """
        user = UserModel.register(TEST_UID, "MyPassword123", TEST_EMAIL, mock_hash_func)

        assert user.verify_password("MyPassword123", mock_verify_func) is True
        assert user.verify_password("mypassword123", mock_verify_func) is False
        assert user.verify_password("MYPASSWORD123", mock_verify_func) is False

    def test_password_verification_with_empty_password(self):
        """
        測試使用空密碼進行驗證
        """
        user = UserModel.register(TEST_UID, "actual_password", TEST_EMAIL, mock_hash_func)
        assert user.verify_password("", mock_verify_func) is False

    def test_password_verification_multiple_times(self):
        """
        測試多次密碼驗證的一致性
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)

        # 多次驗證應該保持一致
        for _ in range(5):
            assert user.verify_password(TEST_PASSWORD, mock_verify_func) is True
            assert user.verify_password("wrong", mock_verify_func) is False


class TestProfileUpdate:
    """測試個人資料更新功能"""

    def test_profile_update_all_fields(self):
        """
        測試更新所有個人資料欄位
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)

        new_name = "John Doe"
        new_birthdate = date(1990, 1, 15)
        new_description = "A software developer."

        user.update_profile(
            name=new_name,
            birthdate=new_birthdate,
            description=new_description
        )

        assert user.profile.name == new_name
        assert user.profile.birthdate == new_birthdate
        assert user.profile.description == new_description

    def test_profile_update_overwrites_previous_data(self):
        """
        測試更新個人資料會覆蓋之前的資料
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)

        # 第一次更新
        user.update_profile("Alice", date(1985, 5, 20), "First description")
        assert user.profile.name == "Alice"

        # 第二次更新應該覆蓋
        user.update_profile("Bob", date(1990, 10, 15), "Second description")
        assert user.profile.name == "Bob"
        assert user.profile.birthdate == date(1990, 10, 15)
        assert user.profile.description == "Second description"

    def test_profile_update_creates_new_profile_instance(self):
        """
        測試更新個人資料會創建新的 Profile 實例（因為 Profile 是 frozen dataclass）
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)

        old_profile = user.profile
        user.update_profile("New Name", date(2000, 1, 1), "New description")

        # 應該是不同的實例
        assert user.profile is not old_profile


class TestUserRole:
    """測試使用者角色功能"""

    def test_default_role_is_normal(self):
        """
        測試新註冊使用者的預設角色是 NORMAL
        """
        user = UserModel.register(TEST_UID, TEST_PASSWORD, TEST_EMAIL, mock_hash_func)
        assert user.role == UserRole.NORMAL

    def test_user_can_have_different_roles(self):
        """
        測試使用者可以有不同的角色
        """
        # 使用建構子創建不同角色的使用者
        admin_user = UserModel(
            id="admin-id",
            uid="admin",
            email="admin@example.com",
            hashed_password=HashedPassword("hashed_password"),
            profile=Profile(),
            role=UserRole.ADMIN
        )

        employee_user = UserModel(
            id="employee-id",
            uid="employee",
            email="employee@example.com",
            hashed_password=HashedPassword("hashed_password"),
            profile=Profile(),
            role=UserRole.EMPLOYEE
        )

        assert admin_user.role == UserRole.ADMIN
        assert employee_user.role == UserRole.EMPLOYEE

    def test_role_enum_values(self):
        """
        測試角色枚舉的值
        """
        assert UserRole.ADMIN.value == "ADMIN"
        assert UserRole.EMPLOYEE.value == "EMPLOYEE"
        assert UserRole.NORMAL.value == "NORMAL"


class TestHashedPassword:
    """測試 HashedPassword 值物件"""

    def test_hashed_password_equality(self):
        """
        測試相同密碼雜湊的相等性
        """
        pwd1 = HashedPassword("hashed_abc123")
        pwd2 = HashedPassword("hashed_abc123")
        pwd3 = HashedPassword("hashed_different")

        assert pwd1 == pwd2
        assert pwd1 != pwd3

    def test_hashed_password_equality_with_non_hashed_password(self):
        """
        測試與非 HashedPassword 物件的比較
        """
        pwd = HashedPassword("hashed_password")

        assert pwd != "hashed_password"  # 字串比較應返回 False
        assert pwd != 123  # 數字比較應返回 False
        assert pwd != None  # None 比較應返回 False

    def test_hashed_password_verify_method(self):
        """
        測試 HashedPassword 的 verify 方法
        """
        pwd = HashedPassword("hashed_test_password")

        assert pwd.verify("test_password", mock_verify_func) is True
        assert pwd.verify("wrong_password", mock_verify_func) is False


class TestProfile:
    """測試 Profile 值物件"""

    def test_profile_creation_with_all_fields(self):
        """
        測試創建包含所有欄位的 Profile
        """
        profile = Profile(
            name="John Doe",
            birthdate=date(1990, 5, 15),
            description="Software Engineer"
        )

        assert profile.name == "John Doe"
        assert profile.birthdate == date(1990, 5, 15)
        assert profile.description == "Software Engineer"

    def test_profile_creation_with_default_values(self):
        """
        測試創建使用預設值的 Profile
        """
        profile = Profile()

        assert profile.name is None
        assert profile.birthdate is None
        assert profile.description is None

    def test_profile_immutability(self):
        """
        測試 Profile 是不可變的（frozen dataclass）
        """
        profile = Profile(name="Alice")

        with pytest.raises(Exception):  # FrozenInstanceError
            profile.name = "Bob"

    def test_profile_equality(self):
        """
        測試 Profile 的相等性比較
        """
        profile1 = Profile(
            name="John",
            birthdate=date(1990, 1, 1),
            description="Dev"
        )
        profile2 = Profile(
            name="John",
            birthdate=date(1990, 1, 1),
            description="Dev"
        )
        profile3 = Profile(
            name="Jane",
            birthdate=date(1990, 1, 1),
            description="Dev"
        )

        assert profile1 == profile2
        assert profile1 != profile3


class TestUserModelConstructor:
    """測試 UserModel 建構子"""

    def test_constructor_creates_user_with_all_fields(self):
        """
        測試使用建構子創建包含所有欄位的使用者
        """
        user_id = "test-user-id"
        uid = "testuser"
        email = "test@example.com"
        hashed_pwd = HashedPassword("hashed_password")
        profile = Profile(name="Test User")
        role = UserRole.EMPLOYEE

        user = UserModel(
            id=user_id,
            uid=uid,
            email=email,
            hashed_password=hashed_pwd,
            profile=profile,
            role=role
        )

        assert user.id == user_id
        assert user.uid == uid
        assert user.email == email
        assert user._hashed_password == hashed_pwd
        assert user.profile == profile
        assert user.role == role

    def test_constructor_with_default_role(self):
        """
        測試建構子使用預設角色
        """
        user = UserModel(
            id="id",
            uid="uid",
            email="email@example.com",
            hashed_password=HashedPassword("pwd"),
            profile=Profile()
        )

        assert user.role == UserRole.NORMAL


class TestUserModelReconstitute:
    """測試 UserModel reconstitute 工廠方法"""

    def test_reconstitute_creates_user_from_persistence(self):
        """
        測試從持久化資料重建使用者
        """
        user = UserModel.reconstitute(
            id="test-uuid",
            uid="testuser",
            email="test@example.com",
            hashed_password="$2b$12$hashedpassword",
            profile=Profile(name="Test User"),
            role=UserRole.ADMIN
        )

        assert user.id == "test-uuid"
        assert user.uid == "testuser"
        assert user.email == "test@example.com"
        assert user._hashed_password.value == "$2b$12$hashedpassword"
        assert user.profile.name == "Test User"
        assert user.role == UserRole.ADMIN
