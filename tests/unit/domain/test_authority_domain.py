import pytest
from app.domain.AuthorityModel import AuthorityModel


# --- Test Data ---
TEST_AUTHORITY_NAME = "USER_READ"
TEST_AUTHORITY_DESCRIPTION = "Permission to read user data"


def test_authority_creation_with_valid_data():
    """
    測試使用有效資料建立權限實體。
    """
    authority = AuthorityModel.create(
        name=TEST_AUTHORITY_NAME,
        description=TEST_AUTHORITY_DESCRIPTION
    )

    # 斷言物件型別正確
    assert isinstance(authority, AuthorityModel)

    # 斷言屬性符合預期
    assert authority.id is None  # ID should be None before persistence
    assert authority.name == TEST_AUTHORITY_NAME
    assert authority.description == TEST_AUTHORITY_DESCRIPTION


def test_authority_creation_without_description():
    """
    測試建立不包含描述的權限實體。
    """
    authority = AuthorityModel.create(name=TEST_AUTHORITY_NAME)

    assert authority.name == TEST_AUTHORITY_NAME
    assert authority.description is None


def test_authority_name_is_converted_to_uppercase():
    """
    測試權限名稱會自動轉換為大寫。
    """
    authority = AuthorityModel.create(name="user_write")

    assert authority.name == "USER_WRITE"


def test_authority_name_is_stripped():
    """
    測試權限名稱會自動去除前後空白。
    """
    authority = AuthorityModel.create(name="  USER_DELETE  ")

    assert authority.name == "USER_DELETE"


def test_authority_creation_with_empty_name_raises_error():
    """
    測試使用空白名稱建立權限時會拋出 ValueError。
    """
    with pytest.raises(ValueError, match="Authority name cannot be empty"):
        AuthorityModel.create(name="")

    with pytest.raises(ValueError, match="Authority name cannot be empty"):
        AuthorityModel.create(name="   ")


def test_authority_update_description():
    """
    測試更新權限描述的功能。
    """
    authority = AuthorityModel.create(name=TEST_AUTHORITY_NAME)

    new_description = "Updated permission description"
    authority.update_description(new_description)

    assert authority.description == new_description


def test_authority_update_description_to_none():
    """
    測試將權限描述更新為 None。
    """
    authority = AuthorityModel.create(
        name=TEST_AUTHORITY_NAME,
        description=TEST_AUTHORITY_DESCRIPTION
    )

    authority.update_description(None)

    assert authority.description is None


def test_authority_equality_by_name():
    """
    測試權限實體的相等性判斷（基於名稱）。
    """
    authority1 = AuthorityModel.create(name="USER_READ", description="Desc 1")
    authority2 = AuthorityModel.create(name="USER_READ", description="Desc 2")
    authority3 = AuthorityModel.create(name="USER_WRITE")

    # 相同名稱的權限應該相等（即使描述不同）
    assert authority1 == authority2

    # 不同名稱的權限應該不相等
    assert authority1 != authority3


def test_authority_hash_consistency():
    """
    測試權限實體的雜湊值一致性。
    """
    authority1 = AuthorityModel.create(name="USER_READ")
    authority2 = AuthorityModel.create(name="USER_READ")

    # 相同名稱的權限應該有相同的雜湊值
    assert hash(authority1) == hash(authority2)


def test_authority_can_be_used_in_set():
    """
    測試權限實體可以用於集合操作。
    """
    authority1 = AuthorityModel.create(name="USER_READ")
    authority2 = AuthorityModel.create(name="USER_READ")  # Duplicate
    authority3 = AuthorityModel.create(name="USER_WRITE")

    authority_set = {authority1, authority2, authority3}

    # 集合應該只包含兩個唯一的權限
    assert len(authority_set) == 2


def test_authority_with_id():
    """
    測試手動建立包含 ID 的權限實體（模擬從資料庫讀取）。
    """
    authority = AuthorityModel(
        id=1,
        name=TEST_AUTHORITY_NAME,
        description=TEST_AUTHORITY_DESCRIPTION
    )

    assert authority.id == 1
    assert authority.name == TEST_AUTHORITY_NAME
    assert authority.description == TEST_AUTHORITY_DESCRIPTION
